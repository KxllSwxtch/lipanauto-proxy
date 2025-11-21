"""
Pydantic schemas for Encar vehicle inspection data
"""
from typing import Optional
from pydantic import BaseModel, Field


class TransmissionType(BaseModel):
    """Transmission type details"""
    title: Optional[str] = Field(default=None, description="Transmission type title")


class GuarantyType(BaseModel):
    """Warranty type details"""
    title: Optional[str] = Field(default=None, description="Warranty type title")


class CarStateType(BaseModel):
    """Car condition/state type"""
    title: Optional[str] = Field(default=None, description="Car state description")


class InspectionDetail(BaseModel):
    """Detailed inspection information"""
    vin: Optional[str] = Field(default=None, description="Vehicle Identification Number")
    mileage: Optional[int] = Field(default=None, description="Vehicle mileage in kilometers")
    firstRegistrationDate: Optional[str] = Field(default=None, description="Date of first registration")
    transmissionType: Optional[TransmissionType] = Field(default=None, description="Transmission details")
    guarantyType: Optional[GuarantyType] = Field(default=None, description="Warranty information")
    carStateType: Optional[CarStateType] = Field(default=None, description="Vehicle condition state")
    engineCheck: Optional[str] = Field(default=None, description="Engine inspection status")
    trnsCheck: Optional[str] = Field(default=None, description="Transmission inspection status")
    tuning: Optional[bool] = Field(default=None, description="Whether vehicle has been tuned/modified")
    recall: Optional[bool] = Field(default=None, description="Whether vehicle has recall issues")
    modelYear: Optional[str] = Field(default=None, description="Model year of the vehicle")
    issueDate: Optional[str] = Field(default=None, description="Issue date of inspection")
    motorType: Optional[str] = Field(default=None, description="Motor/engine type")
    version: Optional[str] = Field(default=None, description="Vehicle version/trim")


class InspectionMaster(BaseModel):
    """Master inspection data"""
    detail: Optional[InspectionDetail] = Field(default=None, description="Detailed inspection information")
    accdient: Optional[bool] = Field(default=None, description="Whether vehicle has accident history")
    simpleRepair: Optional[bool] = Field(default=None, description="Whether vehicle has simple repair history")


class InspectionDataResponse(BaseModel):
    """Complete inspection data response from Encar API"""
    master: Optional[InspectionMaster] = Field(default=None, description="Master inspection data")

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
