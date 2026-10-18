from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="전문 과정")
    duration: Mapped[str] = mapped_column(String(40), default="")
    featured: Mapped[bool] = mapped_column(Boolean, default=False)


class ScheduleModule(Base):
    __tablename__ = "schedule_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order: Mapped[int] = mapped_column(Integer, unique=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    hours: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(40))


class CourseOverview(Base):
    __tablename__ = "course_overviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), unique=True)
    concept: Mapped[str] = mapped_column(Text)
    applications: Mapped[str] = mapped_column(Text)
    data_linkage: Mapped[str] = mapped_column(Text)
    practical_value: Mapped[str] = mapped_column(Text)
    technologies: Mapped[str] = mapped_column(Text)


class TrainingDay(Base):
    __tablename__ = "training_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    training_date: Mapped[date] = mapped_column(Date, index=True)
    weekday: Mapped[str] = mapped_column(String(8))
    daily_hours: Mapped[int] = mapped_column(Integer)
    cumulative_hours: Mapped[int] = mapped_column(Integer)


class TrainingPeriod(Base):
    __tablename__ = "training_periods"
    __table_args__ = (UniqueConstraint("training_day_id", "number", name="uq_day_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_day_id: Mapped[int] = mapped_column(ForeignKey("training_days.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(32))
    start_time: Mapped[str] = mapped_column(String(8))
    end_time: Mapped[str] = mapped_column(String(8))
    subject: Mapped[str] = mapped_column(String(180))
    content: Mapped[str] = mapped_column(Text)
    instructor: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(Text)
