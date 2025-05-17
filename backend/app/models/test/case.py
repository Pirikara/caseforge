from sqlmodel import Field, Relationship
from typing import Optional, List
from ..base import TimestampModel

class TestCase(TimestampModel, table=True):
    __test__ = False
    __tablename__ = "testcase"
    """テストケースモデル（1つのテストパターン）"""
    id: str = Field(index=True, primary_key=True)
    suite_id: str = Field(foreign_key="testsuite.id")
    name: str
    description: Optional[str] = None
    error_type: Optional[str] = None
    
    # リレーションシップ
    test_suite: "TestSuite" = Relationship(back_populates="test_cases")
    test_steps: List["TestStep"] = Relationship(back_populates="test_case", sa_relationship_kwargs={"cascade": "delete, all"})
    test_case_results: List["TestCaseResult"] = Relationship(back_populates="test_case", sa_relationship_kwargs={"cascade": "delete, all"})