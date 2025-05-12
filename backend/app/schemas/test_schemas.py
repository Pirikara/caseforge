from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# TestStep スキーマ
class TestStepBase(BaseModel):
    sequence: int
    name: Optional[str] = None
    method: str
    path: str
    request_headers: Optional[Dict[str, Any]] = None
    request_body: Optional[Any] = None
    request_params: Optional[Dict[str, Any]] = None
    extract_rules: Optional[Dict[str, str]] = None
    expected_status: Optional[int] = None

class TestStepCreate(TestStepBase):
    pass

class TestStepUpdate(TestStepBase):
    pass

class TestStep(TestStepBase):
    id: str
    case_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# TestCase スキーマ
class TestCaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    error_type: Optional[str] = None

class TestCaseCreate(TestCaseBase):
    steps: List[TestStepCreate]

class TestCaseUpdate(TestCaseBase):
    steps: Optional[List[TestStepUpdate]] = None

class TestCase(TestCaseBase):
    id: str
    suite_id: str
    created_at: datetime
    steps: List[TestStep] = []

    model_config = ConfigDict(from_attributes=True)

# TestSuite スキーマ
class TestSuiteBase(BaseModel):
    target_method: str
    target_path: str
    name: str
    description: Optional[str] = None

class TestSuiteCreate(TestSuiteBase):
    test_cases: List[TestCaseCreate]

class TestSuiteUpdate(TestSuiteBase):
    test_cases: Optional[List[TestCaseUpdate]] = None

class TestSuite(TestSuiteBase):
    id: str
    project_id: str
    created_at: datetime
    test_cases: List[TestCase] = []

    model_config = ConfigDict(from_attributes=True)

# StepResult スキーマ
class StepResultBase(BaseModel):
    status_code: Optional[int] = None
    passed: bool
    response_body: Optional[Any] = None
    error_message: Optional[str] = None
    response_time: Optional[int] = None
    method: str # 追加
    path: str # 追加
    extracted_values: Optional[Dict[str, Any]] = None # 追加

class StepResultCreate(StepResultBase):
    step_id: str

class StepResult(StepResultBase):
    id: str
    test_case_result_id: str
    step_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# TestCaseResult スキーマ
class TestCaseResultBase(BaseModel):
    status: str
    error_message: Optional[str] = None

class TestCaseResultCreate(TestCaseResultBase):
    case_id: str
    step_results: List[StepResultCreate]

class TestCaseResult(TestCaseResultBase):
    id: str
    test_run_id: str
    case_id: str
    created_at: datetime
    step_results: List[StepResult] = []

    model_config = ConfigDict(from_attributes=True)

# TestRun スキーマ
class TestRunBase(BaseModel):
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None

class TestRunCreate(BaseModel):
    suite_id: str # TestSuite ID を指定して実行

class TestRun(TestRunBase):
    id: str
    suite_id: str
    test_case_results: List[TestCaseResult] = [] # 実行結果に紐づくTestCaseResult

    model_config = ConfigDict(from_attributes=True)

# API レスポンス用スキーマ (ネストされた構造)
class TestSuiteWithCasesAndSteps(TestSuite):
    test_cases: List[TestCase] = []

class TestCaseWithSteps(TestCase):
    steps: List[TestStep] = []

class TestRunWithResults(TestRun):
    test_case_results: List[TestCaseResult] = []

class TestCaseResultWithSteps(TestCaseResult):
    step_results: List[StepResult] = []

# テスト実行履歴サマリー用スキーマ
class TestRunSummary(BaseModel):
    id: str # TestRun の id (str)
    run_id: str
    suite_id: str
    suite_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    test_cases_count: int
    passed_test_cases: int
    success_rate: float