from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String
from pydantic import BaseModel
from typing import List

# Async MySQL database URL
DATABASE_URL = "mysql+aiomysql://root:Prema$1998@localhost/student_management_1"  # Connection string for the MySQL database using the aiomysql driver.

# Async SQLAlchemy setup
Base = declarative_base()  # Base class for declaring database models.
async_engine = create_async_engine(DATABASE_URL, echo=True)  # Creates an asynchronous engine for connecting to the database.
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)  # Creates a session factory for managing database sessions.

# Database Dependency
async def get_db():
    """
    Dependency function to provide a database session for each request.
    Ensures proper handling of sessions with async context management.
    """
    async with AsyncSessionLocal() as session:
        yield session

# Database Model
class Student(Base):
    """
    SQLAlchemy model representing the 'students' table in the database.
    """
    __tablename__ = "students"  # Name of the table in the database.
    id = Column(Integer, primary_key=True, index=True)  # Primary key column.
    name = Column(String(100), nullable=False)  # Name column (required).
    age = Column(Integer, nullable=False)  # Age column (required).
    address = Column(String(255), nullable=False)  # Address column (required).
    email = Column(String(100), unique=True, nullable=False)  # Email column (unique and required).

# Pydantic Schemas
class StudentCreate(BaseModel):
    """
    Pydantic schema for validating incoming student data.
    """
    name: str
    age: int
    address: str
    email: str

class StudentOut(StudentCreate):
    """
    Pydantic schema for returning student data in API responses.
    Includes the 'id' field and allows ORM compatibility.
    """
    id: int

    class Config:
        orm_mode = True  # Enables ORM mode for automatic conversion of database objects.

# FastAPI Instance
app = FastAPI()  # Creates a FastAPI application instance.

# Initialize the database
@app.on_event("startup")
async def startup():
    """
    Event handler to run during application startup.
    Ensures that all tables are created in the database.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Routes

@app.get("/students", response_model=List[StudentOut])
async def get_students(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to retrieve all students from the database.
    - Queries the database for all students.
    - Returns a list of students.
    """
    result = await db.execute("SELECT * FROM students")  # Raw SQL query to fetch all students.
    students = result.fetchall()  # Fetch all rows from the result.
    return [dict(row) for row in students]  # Convert rows to dictionaries for JSON response.

@app.get("/students/{student_id}", response_model=StudentOut)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to retrieve a specific student by ID.
    - Queries the database for the student with the given ID.
    - Returns the student details or raises a 404 error if not found.
    """
    result = await db.execute(f"SELECT * FROM students WHERE id = {student_id}")  # Query for a specific student.
    student = result.fetchone()  # Fetch one row from the result.
    if not student:  # If no student is found, raise a 404 error.
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(student)  # Convert the row to a dictionary for JSON response.

@app.post("/students", response_model=StudentOut)
async def create_student(student: StudentCreate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to create a new student.
    - Accepts student details in the request body.
    - Adds the new student to the database and returns the created student.
    """
    new_student = Student(**student.dict())  # Create a new Student object from the request data.
    db.add(new_student)  # Add the new student to the session.
    await db.commit()  # Commit the transaction to save the student.
    await db.refresh(new_student)  # Refresh the instance with the saved data.
    return new_student  # Return the newly created student.

@app.put("/students/{student_id}", response_model=StudentOut)
async def update_student(student_id: int, updated_student: StudentCreate, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to update an existing student's details.
    - Queries the database for the student by ID.
    - Updates the student's details if they exist, or raises a 404 error.
    """
    query = await db.execute(f"SELECT * FROM students WHERE id = {student_id}")  # Query for the existing student.
    existing_student = query.fetchone()  # Fetch the student row.
    if not existing_student:  # If no student is found, raise a 404 error.
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Update the student details using raw SQL.
    await db.execute(
        f"UPDATE students SET name='{updated_student.name}', age={updated_student.age}, "
        f"address='{updated_student.address}', email='{updated_student.email}' WHERE id={student_id}"
    )
    await db.commit()  # Commit the transaction to save changes.
    return {"id": student_id, **updated_student.dict()}  # Return the updated student data.

@app.delete("/students/{student_id}")
async def delete_student(student_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to delete a student by ID.
    - Queries the database for the student by ID.
    - Deletes the student if they exist, or raises a 404 error.
    """
    query = await db.execute(f"SELECT * FROM students WHERE id = {student_id}")  # Query for the student.
    existing_student = query.fetchone()  # Fetch the student row.
    if not existing_student:  # If no student is found, raise a 404 error.
        raise HTTPException(status_code=404, detail="Student not found")
    
    await db.execute(f"DELETE FROM students WHERE id = {student_id}")  # Delete the student.
    await db.commit()  # Commit the transaction to apply the deletion.
    return {"message": f"Student with ID {student_id} deleted"}  # Return a success message.

