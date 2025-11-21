"""
Pydantic schemas for Encar vehicle inspection data
"""
from typing import Optional
from pydantic import BaseModel, Field


class TransmissionType(BaseModel):
    """Transmission type details"""
    title: str = Field(..., description="Transmission type title")


class GuarantyType(BaseModel):
    """Warranty type details"""
    title: str = Field(..., description="Warranty type title")


class CarStateType(BaseModel):
    """Car condition/state type"""
    title: str = Field(..., description="Car state description")


class InspectionDetail(BaseModel):
    """Detailed inspection information"""
    vin: str = Field(..., description="Vehicle Identification Number")
    mileage: int = Field(..., description="Vehicle mileage in kilometers")
    firstRegistrationDate: str = Field(..., description="Date of first registration")
    transmissionType: TransmissionType = Field(..., description="Transmission details")
    guarantyType: GuarantyType = Field(..., description="Warranty information")
    carStateType: CarStateType = Field(..., description="Vehicle condition state")
    engineCheck: str = Field(..., description="Engine inspection status")
    trnsCheck: str = Field(..., description="Transmission inspection status")
    tuning: bool = Field(..., description="Whether vehicle has been tuned/modified")
    recall: bool = Field(..., description="Whether vehicle has recall issues")
    modelYear: str = Field(..., description="Model year of the vehicle")
    issueDate: str = Field(..., description="Issue date of inspection")
    motorType: str = Field(..., description="Motor/engine type")
    version: str = Field(..., description="Vehicle version/trim")


class InspectionMaster(BaseModel):
    """Master inspection data"""
    detail: InspectionDetail = Field(..., description="Detailed inspection information")
    accdient: bool = Field(..., description="Whether vehicle has accident history")
    simpleRepair: bool = Field(..., description="Whether vehicle has simple repair history")


class InspectionDataResponse(BaseModel):
    """Complete inspection data response from Encar API"""
    master: InspectionMaster = Field(..., description="Master inspection data")

    model_config = {
        "json_schema_extra": {
            "example": {
                "master": {
                    "detail": {
                        "vin": "KMHXX00XXXX000000",
                        "mileage": 45000,
                        "firstRegistrationDate": "2020-01-15",
                        "transmissionType": {"title": "자동"},
                        "guarantyType": {"title": "보증"},
                        "carStateType": {"title": "양호"},
                        "engineCheck": "정상",
                        "trnsCheck": "정상",
                        "tuning": False,
                        "recall": False,
                        "modelYear": "2020",
                        "issueDate": "2024-01-15",
                        "motorType": "가솔린",
                        "version": "2.0 프리미엄"
                    },
                    "accdient": False,
                    "simpleRepair": False
                }
            }
        }
    }
