"""API response handling for Apache CloudStack."""

from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict
from enum import Enum


class ResponseStatus(Enum):
    """CloudStack API response status."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


@dataclass
class CloudStackResponse:
    """Represents a CloudStack API response."""
    
    status: ResponseStatus
    response_data: Dict[str, Any] = field(default_factory=dict)
    job_id: Optional[str] = None
    job_status: Optional[int] = None
    job_result: Optional[Dict[str, Any]] = None
    error_code: Optional[int] = None
    error_text: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """Check if the response was successful."""
        return self.status == ResponseStatus.SUCCESS
    
    @property
    def is_complete(self) -> bool:
        """Check if async job is complete."""
        if self.job_status is not None:
            return self.job_status == 1
        return self.is_success
    
    def get_result(self, key: str, default: Any = None) -> Any:
        """Get a value from the response data."""
        return self.response_data.get(key, default)
    
    def get_list(self, key: str) -> List[Dict[str, Any]]:
        """Get a list from the response data."""
        data = self.response_data.get(key, [])
        if isinstance(data, list):
            return data
        return []
    
    def get_first(self, key: str) -> Optional[Dict[str, Any]]:
        """Get the first item from a list in the response data."""
        items = self.get_list(key)
        return items[0] if items else None


@dataclass
class AsyncJobResponse:
    """Represents an async job response from CloudStack."""
    
    job_id: str
    job_status: int
    job_result_code: Optional[int] = None
    job_result: Optional[Dict[str, Any]] = None
    job_progress_status: Optional[int] = None
    job_created: Optional[str] = None
    job_completed: Optional[str] = None
    job_result_text: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if the job is complete."""
        return self.job_status == 1
    
    @property
    def is_failed(self) -> bool:
        """Check if the job failed."""
        return self.job_status == 2
    
    @property
    def is_pending(self) -> bool:
        """Check if the job is still pending."""
        return self.job_status == 0
    
    @property
    def is_cancelled(self) -> bool:
        """Check if the job was cancelled."""
        return self.job_status == 3


@dataclass
class APIListResponse:
    """Represents a list API response from CloudStack."""
    
    count: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)
    response: Optional[Dict[str, Any]] = None
    
    @property
    def is_empty(self) -> bool:
        """Check if the list is empty."""
        return self.count == 0
    
    def __iter__(self):
        """Iterate over items."""
        return iter(self.items)
    
    def __len__(self) -> int:
        """Get the count of items."""
        return self.count
    
    def __getitem__(self, index: int) -> Dict[str, Any]:
        """Get item by index."""
        return self.items[index]


@dataclass
class TagResponse:
    """Represents a tag response from CloudStack."""
    
    resource_type: str
    resource_id: str
    key: str
    value: str


@dataclass  
class UsageRecord:
    """Represents a usage record from CloudStack."""
    
    account: str
    domain_id: str
    zone_id: str
    description: str
    usage: float
    usage_type: int
    raw_usage: float
    virtual_size: int
    cpu_count: int
    memory: int
    start_date: str
    end_date: str


def parse_response(response: Dict[str, Any]) -> CloudStackResponse:
    """Parse a CloudStack API response into a CloudStackResponse object."""
    
    # Check for error response
    if "errorcode" in response:
        error = response.get("error", {})
        return CloudStackResponse(
            status=ResponseStatus.FAILURE,
            error_code=response.get("errorcode"),
            error_text=error.get("errortext", "Unknown error"),
            response_data=response
        )
    
    # Check for async job result
    if "jobid" in response:
        job_id = response.get("jobid")
        jobstatus = response.get("jobstatus", -1)
        
        # Handle async job responses
        if jobstatus == -1:
            # Job still running
            return CloudStackResponse(
                status=ResponseStatus.PENDING,
                job_id=job_id,
                job_status=0,
                response_data=response
            )
        elif jobstatus == 0:
            # Job still pending
            return CloudStackResponse(
                status=ResponseStatus.PENDING,
                job_id=job_id,
                job_status=0,
                response_data=response
            )
        elif jobstatus == 1:
            # Job completed successfully
            return CloudStackResponse(
                status=ResponseStatus.SUCCESS,
                job_id=job_id,
                job_status=jobstatus,
                job_result=response.get("jobresult", {}),
                response_data=response
            )
        elif jobstatus == 2:
            # Job failed
            error = response.get("jobresult", {})
            return CloudStackResponse(
                status=ResponseStatus.FAILURE,
                job_id=job_id,
                job_status=jobstatus,
                error_code=500,
                error_text=error.get("errortext", "Job failed"),
                response_data=response
            )
    
    # Standard synchronous response
    if response.get("success", True):
        return CloudStackResponse(
            status=ResponseStatus.SUCCESS,
            response_data=response
        )
    
    return CloudStackResponse(
        status=ResponseStatus.FAILURE,
        error_text=response.get("text", "Unknown error"),
        response_data=response
    )


def parse_list_response(response: Dict[str, Any], list_key: str) -> APIListResponse:
    """Parse a CloudStack list API response."""
    
    count = response.get(f"{list_key}count", 0)
    items = response.get(list_key, [])
    
    if not isinstance(items, list):
        items = [items] if items else []
    
    return APIListResponse(
        count=count,
        items=items,
        response=response
    )