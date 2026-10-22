from dataclasses import dataclass,field

# Extraction Template
@dataclass
class Section:
    text :  str
    source : str                                 
    heading_path: list[str] = field(default_factory=list)  
    page: int | None = None                     
    format: str = ""
    doc_id: str = ""   

