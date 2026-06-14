from pydantic import BaseModel, Field
class ResolveRequest(BaseModel):
    linkedin_url: str = Field(..., description = "URL of a LinkedIn job listing page")

class JobSourceResult(BaseModel):
    company_name: str
    careers_url : str
    position_url : str

class NavigationResult(BaseModel):
    careers_url:str
    position_url:str

