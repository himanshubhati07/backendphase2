"""Thin DRF entry points for stories and activities."""
from __future__ import annotations

from typing import Any

from config.openapi import (
    JWT_SECURITY, LIMIT_PARAMETER, OFFSET_PARAMETER, PUBLIC_SECURITY,
    empty_success_envelope, offset_success_envelope, responses, success_envelope,
)
from config.responses import success_response
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView

from .models import Activity, Story
from .selectors import active_story_or_404, active_stories, public_activities, search_active_stories
from .serializers import ActivityReadSerializer, ActivityWriteSerializer, StoryReadSerializer, StoryWriteSerializer
from .services import create_activity, create_story, delete_activity, delete_story, replace_activity, replace_story


class EnvelopePaginationMixin:
    """Converts DRF's native pagination response into the standard envelope."""

    def paginated_success(self, data: Any, message: str):
        page = self.paginate_queryset(data)
        if page is None:
            return success_response(data, message)
        response = self.get_paginated_response(page)
        return success_response(response.data, message)


class StoryCollectionView(EnvelopePaginationMixin, GenericAPIView):
    serializer_class = StoryReadSerializer
    def get_permissions(self) -> list[Any]:
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    @extend_schema(
        responses=responses(200, offset_success_envelope("StoryListSuccess", StoryReadSerializer()), 401, 500),
        parameters=[LIMIT_PARAMETER, OFFSET_PARAMETER,
                    OpenApiParameter("category", OpenApiTypes.UUID, OpenApiParameter.QUERY, description="Only stories in this category UUID."),
                    OpenApiParameter("age_group", str, OpenApiParameter.QUERY, description="Age group filter (currently `2-3`)."),
                    OpenApiParameter("language", str, OpenApiParameter.QUERY, description="Language filter (currently `en`).")],
        auth=PUBLIC_SECURITY, operation_id="listStories",
        description="List active public stories using optional catalogue filters and offset pagination.",
    )
    def get(self, request: Any):
        queryset = active_stories(
            category=request.query_params.get("category"),
            age_group=request.query_params.get("age_group"),
            language=request.query_params.get("language"),
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            response = self.get_paginated_response(StoryReadSerializer(page, many=True).data)
            return success_response(response.data, "Stories retrieved.")
        return success_response(StoryReadSerializer(queryset, many=True).data, "Stories retrieved.")

    @extend_schema(
        request=StoryWriteSerializer,
        responses=responses(201, success_envelope("StoryCreateSuccess", StoryReadSerializer()), 400, 401, 403, 500),
        auth=JWT_SECURITY, operation_id="createStory",
        description="Create a story. A JWT bearer token is required.",
    )
    def post(self, request: Any):
        serializer = StoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        story = create_story(validated_data=serializer.validated_data)
        return success_response(StoryReadSerializer(story).data, "Story created.", status_code=status.HTTP_201_CREATED)


class StoryDetailView(APIView):
    serializer_class = StoryReadSerializer
    def get_permissions(self) -> list[Any]:
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    @extend_schema(
        responses=responses(200, success_envelope("StoryDetailSuccess", StoryReadSerializer()), 401, 404, 500),
        auth=PUBLIC_SECURITY, operation_id="retrieveStory",
        description="Retrieve one active public story by UUID.",
    )
    def get(self, request: Any, id: object):
        return success_response(StoryReadSerializer(active_story_or_404(id)).data, "Story retrieved.")

    @extend_schema(
        request=StoryWriteSerializer,
        responses=responses(200, success_envelope("StoryUpdateSuccess", StoryReadSerializer()), 400, 401, 403, 404, 500),
        auth=JWT_SECURITY, operation_id="replaceStory",
        description="Replace a story by UUID. A JWT bearer token is required.",
    )
    def put(self, request: Any, id: object):
        story = get_object_or_404(Story.objects.select_related("category"), pk=id)
        serializer = StoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        story = replace_story(story=story, validated_data=serializer.validated_data)
        return success_response(StoryReadSerializer(story).data, "Story updated.")

    @extend_schema(
        responses=responses(200, empty_success_envelope("StoryDeleteSuccess"), 401, 403, 404, 500),
        auth=JWT_SECURITY, operation_id="deleteStory",
        description="Delete a story by UUID. A JWT bearer token is required.",
    )
    def delete(self, request: Any, id: object):
        delete_story(story=get_object_or_404(Story, pk=id))
        return success_response(None, "Story deleted.")


class StorySearchView(EnvelopePaginationMixin, GenericAPIView):
    serializer_class = StoryReadSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        responses=responses(200, offset_success_envelope("StorySearchSuccess", StoryReadSerializer()), 401, 500),
        parameters=[LIMIT_PARAMETER, OFFSET_PARAMETER,
                    OpenApiParameter("q", str, OpenApiParameter.QUERY, description="Search term matched against public story text."),
                    OpenApiParameter("keyword", str, OpenApiParameter.QUERY, description="Alias for `q`; used when `q` is absent.")],
        auth=PUBLIC_SECURITY, operation_id="searchStories",
        description="Search active public stories and return offset-paginated results.",
    )
    def get(self, request: Any):
        queryset = search_active_stories(request.query_params.get("q") or request.query_params.get("keyword"))
        page = self.paginate_queryset(queryset)
        if page is not None:
            response = self.get_paginated_response(StoryReadSerializer(page, many=True).data)
            return success_response(response.data, "Stories retrieved.")
        return success_response(StoryReadSerializer(queryset, many=True).data, "Stories retrieved.")


class StoryActivityCollectionView(EnvelopePaginationMixin, GenericAPIView):
    serializer_class = ActivityReadSerializer
    def get_permissions(self) -> list[Any]:
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    @extend_schema(
        responses=responses(200, offset_success_envelope("ActivityListSuccess", ActivityReadSerializer()), 401, 404, 500),
        parameters=[LIMIT_PARAMETER, OFFSET_PARAMETER], auth=PUBLIC_SECURITY,
        operation_id="listStoryActivities",
        description="List activities for an active public story, using offset pagination.",
    )
    def get(self, request: Any, story_id: object):
        queryset = public_activities(story_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            response = self.get_paginated_response(ActivityReadSerializer(page, many=True).data)
            return success_response(response.data, "Activities retrieved.")
        return success_response(ActivityReadSerializer(queryset, many=True).data, "Activities retrieved.")

    @extend_schema(
        request=ActivityWriteSerializer,
        responses=responses(201, success_envelope("ActivityCreateSuccess", ActivityReadSerializer()), 400, 401, 403, 404, 500),
        auth=JWT_SECURITY, operation_id="createStoryActivity",
        description="Add an activity to a story. A JWT bearer token is required.",
    )
    def post(self, request: Any, story_id: object):
        story = get_object_or_404(Story, pk=story_id)
        serializer = ActivityWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = create_activity(story=story, validated_data=serializer.validated_data)
        return success_response(ActivityReadSerializer(activity).data, "Activity created.", status_code=status.HTTP_201_CREATED)


class ActivityDetailView(APIView):
    serializer_class = ActivityWriteSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ActivityWriteSerializer,
        responses=responses(200, success_envelope("ActivityUpdateSuccess", ActivityReadSerializer()), 400, 401, 403, 404, 500),
        auth=JWT_SECURITY, operation_id="replaceActivity",
        description="Replace an activity by UUID. A JWT bearer token is required.",
    )
    def put(self, request: Any, id: object):
        serializer = ActivityWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = replace_activity(activity=get_object_or_404(Activity, pk=id), validated_data=serializer.validated_data)
        return success_response(ActivityReadSerializer(activity).data, "Activity updated.")

    @extend_schema(
        responses=responses(200, empty_success_envelope("ActivityDeleteSuccess"), 401, 403, 404, 500),
        auth=JWT_SECURITY, operation_id="deleteActivity",
        description="Delete an activity by UUID. A JWT bearer token is required.",
    )
    def delete(self, request: Any, id: object):
        delete_activity(activity=get_object_or_404(Activity, pk=id))
        return success_response(None, "Activity deleted.")
