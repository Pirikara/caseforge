import json
import os
import yaml
import logging
from app.workers import celery_app
from app.services.chain_generator import DependencyAwareRAG, ChainStore
from app.services.schema import get_schema_content
from app.services.endpoint_chain_generator import EndpointChainGenerator
from app.config import settings
from app.models import Endpoint, Service
from sqlmodel import select, Session
from app.models import engine
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

@celery_app.task
def generate_test_suites_task(service_id: int, error_types: Optional[List[str]] = None):
    """
    OpenAPIスキーマから依存関係を考慮したテストスイートを生成するCeleryタスク
    
    Args:
        service_id: サービスID (int)
        
    Returns:
        dict: 生成結果の情報
    """
    
    try:
        schema_path = f"{settings.SCHEMA_DIR}/{str(service_id)}"
        schema_files = [f for f in os.listdir(schema_path) if f.endswith(('.yaml', '.yml', '.json'))]
        
        if not schema_files:
            return {"status": "error", "message": "No schema files found"}
        
        schema_file = schema_files[0]
        schema_content = get_schema_content(str(service_id), schema_file)
        
        if schema_file.endswith('.json'):
            schema = json.loads(schema_content)
        else:
            schema = yaml.safe_load(schema_content)
        
        rag = DependencyAwareRAG(service_id, schema, error_types)
        
        test_suites = rag.generate_request_chains()
        
        chain_store = ChainStore()
        chain_store.save_suites(None, service_id, test_suites) # Pass None for session as it's handled internally in save_suites
        
        return {"status": "completed", "count": len(test_suites)}
        
    except Exception as e:
        logger.error(f"Error generating test suites: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@celery_app.task
def generate_test_suites_for_endpoints_task(service_id: int, endpoint_ids: List[str], error_types: Optional[List[str]] = None) -> Dict:
    """
    選択したエンドポイントからテストスイートを生成するタスク
    
    Args:
        service_id: サービスID (int)
        endpoint_ids: 選択したエンドポイントIDのリスト
        
    Returns:
        生成結果
    """
    try:
        with Session(engine) as session:
            service_query = select(Service).where(Service.id == service_id)
            db_service = session.exec(service_query).first()
            
            if not db_service:
                logger.error(f"Service not found: {service_id}")
                return {"status": "error", "message": "Service not found"}
            

            endpoints_query = select(Endpoint).where(
                Endpoint.service_id == db_service.id,
                Endpoint.endpoint_id.in_(endpoint_ids)
            )
            selected_endpoints = session.exec(endpoints_query).all()

            if not selected_endpoints:
                logger.warning(f"No valid endpoints selected for service {service_id}")
                return {"status": "warning", "message": "No test suites were generated for the selected endpoints."}

            schema_path = f"{settings.SCHEMA_DIR}/{str(service_id)}"
            schema_files = [f for f in os.listdir(schema_path) if f.endswith(('.yaml', '.yml', '.json'))]
            
            if not schema_files:
                return {"status": "error", "message": "No schema files found"}
            
            schema_file = schema_files[0]
            schema_content = get_schema_content(str(service_id), schema_file)
            
            if schema_file.endswith('.json'):
                schema = json.loads(schema_content)
            else:
                schema = yaml.safe_load(schema_content)

            generated_suites_count = 0
            all_generated_suites = []
            
            generator = EndpointChainGenerator(service_id, selected_endpoints, schema, error_types)
            
            generated_suites = generator.generate_chains()
            for i, suite in enumerate(generated_suites):
                if suite.get('test_cases'):
                    first_case = suite['test_cases'][0]
                    if first_case.get('test_steps'):
                        first_step = first_case['test_steps'][0]

            if generated_suites:
                chain_store = ChainStore()
                chain_store.save_suites(session, service_id, generated_suites, overwrite=False)
                generated_suites_count = len(generated_suites)

        if generated_suites_count == 0:
                return {"status": "warning", "message": "No test suites were generated for the selected endpoints."}

        return {"status": "success", "message": f"Successfully generated and saved {generated_suites_count} test suites."}

    except Exception as e:
        logger.error(f"Error generating test suites for service {service_id}: {e}", exc_info=True)
        try:
            session.rollback()
        except Exception as rollback_error:
            logger.error(f"Error rolling back session after task error: {rollback_error}")
        return {"status": "error", "message": str(e)}
