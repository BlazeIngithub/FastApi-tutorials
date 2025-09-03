from fastapi import FastAPI, Path, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional
import json 

app = FastAPI()

class Patient(BaseModel):
    id: Annotated[str, Field(..., description="The ID of the patient", example="P001")]
    name: Annotated[str, Field(..., description="Name of the Patient")]
    city: Annotated[str, Field(..., description="Name of the City")]
    age: Annotated[int, Field(..., gt=0, lt=120, description="Age of the Patient", example=30)]        
    gender: Annotated[Literal['male', 'female', 'others'], Field(..., description="Gender of the Patient", example="male")]
    height: Annotated[float, Field(..., gt=0, description="Height of the Patient in meters")]    
    weight: Annotated[float, Field(..., gt=0, description="Weight of the Patient in kg")] 

    @computed_field
    @property
    def bmi(self) -> float:
        bmi = round(self.weight / (self.height ** 2), 2)
        return bmi
    
    @computed_field
    @property
    def verdict(self) -> str:
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25:
            return "Normal weight"
        elif self.bmi < 30:
            return "Overweight"
        else:
            return "Obesity"

class Patientupdate(BaseModel):
    name: Annotated[Optional[str], Field(default=None, description="Name of the Patient")]
    city: Annotated[Optional[str], Field(default=None, description="Name of the City")]
    age: Annotated[Optional[int], Field(default=None, gt=0, lt=120, description="Age of the Patient")]
    gender: Annotated[Optional[Literal['male', 'female', 'others']], Field(default=None, description="Gender of the Patient")]
    height: Annotated[Optional[float], Field(default=None, gt=0, description="Height of the Patient in meters")]
    weight: Annotated[Optional[float], Field(default=None, gt=0, description="Weight of the Patient in kg")]

def load_data():
    try:
        with open('patients.json', 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_data(data):
    with open('patients.json', 'w') as file:
        json.dump(data, file, indent=2)

@app.get("/")   
def hello():
    return {"message": "Patient Management System API"} 

@app.get('/about')
def about():
    return {"message": "A fully functional Patient Management System API to build your records and manage your patients."} 

@app.get('/view')
def view():
    data = load_data()
    return {"patients": data}

@app.get('/patient/{patient_id}')
def view_patient(patient_id: str = Path(..., description="The ID of the patient to view", example="P001")):
    # Load all the patients
    data = load_data()

    if patient_id in data:  
        return {"patient": data[patient_id]}
    raise HTTPException(status_code=404, detail="Patient not found")

@app.get('/sort')
def sort_patients(sort_by: str = Query(..., description="sort on the basis of weight, height or bmi"), order: str = Query("asc", description="Order of sorting: asc or desc")):
    valid_fields = ['height', 'weight', 'bmi']

    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f'Invalid field select from {valid_fields}')

    if order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail='Order must be either asc or desc')

    data = load_data()

    sort_order = True if order == 'desc' else False

    sorted_data = sorted(data.values(), key=lambda x: x.get(sort_by, 0), reverse=sort_order)

    return {"sorted_patients": sorted_data}

@app.post('/create')
def create_patient(patient: Patient):
    # Load existing data
    data = load_data()
    # Check if the patient already exists

    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient with this ID already exists")
    
    # Add new patient to the database (exclude ID from stored data)
    data[patient.id] = patient.model_dump(exclude={'id'})

    # Save to the JSON file
    save_data(data)

    return JSONResponse(status_code=201, content={"message": "Patient created successfully", "patient": data[patient.id]})

@app.put('/update/{patient_id}')
def update_patient(patient_id: str, patient_update: Patientupdate):
    data = load_data()

    if patient_id not in data: 
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get existing patient info (make a copy to avoid modifying original)
    existing_patient_info = data[patient_id].copy()
    
    # Get updated fields (only non-None values)
    updated_patient_info = patient_update.model_dump(exclude_unset=True)

    # Update existing info with new values
    for key, value in updated_patient_info.items():
        existing_patient_info[key] = value

    # Add ID to create complete Patient object for BMI/verdict calculation
    existing_patient_info['id'] = patient_id
    
    # Create Patient object to get updated BMI and verdict
    patient_pydantic_object = Patient(**existing_patient_info)

    # Convert back to dict and exclude ID for storage
    updated_patient_dict = patient_pydantic_object.model_dump(exclude={'id'})

    # Update data
    data[patient_id] = updated_patient_dict

    # Save data
    save_data(data)

    return JSONResponse(status_code=200, content={
        "message": "Patient updated successfully", 
        "patient": updated_patient_dict
    })


@app.delete('/delete/{patient_id}')
def delete_patient(patient_id: str):
    
    #Load data

    data = load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    del data[patient_id]

    save_data(data)

    return JSONResponse(status_code=200, content={"message": "Patient deleted successfully"})