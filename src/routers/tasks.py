from datetime import datetime

from fastapi import APIRouter, Request

from database import db, filter_by
from models import User, UserTask
from schemas.task import Task as Ta
from utils.auth import get_token, user_auth
from utils.exceptions import InvalidTask, PermissionDeniedError


router = APIRouter(tags=["/tasks"])


@router.post("/tasks/new", dependencies=[user_auth])
async def new_task(request: Request, task: Ta):
    user = await User.get_user_by_token(get_token(request))
    task_obj = await UserTask.create(task.title, task.description, task.end, task.priority, user)
    return task_obj.serialize


@router.get("/tasks/all", dependencies=[user_auth])
async def all_tasks(request: Request):
    user = await User.get_user_by_token(get_token(request))
    tasks = await db.all(filter_by(UserTask, creator_id=user.id))
    return tasks


@router.delete("/tasks/delete", dependencies=[user_auth])
async def delete_task(request: Request, task_id: int):
    user = await User.get_user_by_token(get_token(request))
    task = await db.get(UserTask, id=task_id)
    if not task:
        raise InvalidTask

    if task not in user.tasks or not user.admin:
        raise PermissionDeniedError

    await task.remove()
    return True


@router.post("/tasks/edit", dependencies=[user_auth])
async def edit_task(
        request: Request,
        task_id: int,
        title: str | None = None,
        description: str | None = None,
        priority: int | None = None,
        end: datetime | None = None
):
    print(request.headers)
    user = await User.get_user_by_token(get_token(request))
    task = await db.get(UserTask, id=task_id)
    if not task:
        raise InvalidTask

    if task not in user.tasks or not user.admin:
        raise PermissionDeniedError

    if title:
        task.title = title
    if description:
        task.description = description
    if priority:
        task.priority = priority
    if end:
        task.end = end

    return task


@router.post("/tasks/resolve", dependencies=[user_auth])
async def resolve_task(request: Request, task_id: int):
    user = await User.get_user_by_token(get_token(request))
    task = await db.get(UserTask, id=task_id)
    if not task:
        raise InvalidTask

    if task not in user.tasks or not user.admin:
        raise PermissionDeniedError

    task.resolved = True

    return task
