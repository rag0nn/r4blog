from django.contrib.auth import authenticate
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from content.models import Note, Post, Project
from content.services import can_view, create_content, update_content

from .serializers import ContentWriteSerializer, content_response


class TokenLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = authenticate(request=request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class TokenRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if isinstance(request.auth, Token):
            request.auth.delete()
        else:
            Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContentCreateView(APIView):
    permission_classes = [IsAuthenticated]
    model = None

    def post(self, request):
        serializer = ContentWriteSerializer(
            data=request.data, context={"creating": True}
        )
        serializer.is_valid(raise_exception=True)
        item = create_content(
            self.model,
            request.user,
            serializer.validated_data["parsed_markdown"],
            serializer.validated_data.get("visibility", "public"),
        )
        return Response(content_response(item), status=status.HTTP_201_CREATED)


class ContentUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    model = None

    def _update(self, request, slug, partial):
        item = get_object_or_404(self.model.objects, slug=slug)
        if item.visibility == "private" and not can_view(item, request.user):
            raise Http404
        if item.owner_id != request.user.pk:
            return Response(
                {"detail": "Only the owner can update this content."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ContentWriteSerializer(
            data=request.data,
            partial=partial,
            context={"creating": False},
        )
        serializer.is_valid(raise_exception=True)
        if (
            serializer.validated_data.get("parsed_markdown") is None
            and "visibility" not in serializer.validated_data
        ):
            return Response(
                {"detail": "Provide Markdown content, a .md file, or visibility."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item = update_content(
            item,
            request.user,
            serializer.validated_data.get("parsed_markdown"),
            serializer.validated_data.get("visibility"),
        )
        return Response(content_response(item))

    def put(self, request, slug):
        return self._update(request, slug, partial=False)

    def patch(self, request, slug):
        return self._update(request, slug, partial=True)


class ContentDownloadView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [AllowAny]
    model = None

    def get(self, request, slug):
        item = get_object_or_404(self.model.objects, slug=slug)
        if not can_view(item, request.user):
            raise Http404
        response = HttpResponse(item.markdown, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{item.slug}.md"'
        response["X-Content-Type-Options"] = "nosniff"
        if item.visibility == "private":
            response["Cache-Control"] = "private, no-store"
        return response


class PostCreateView(ContentCreateView):
    model = Post


class NoteCreateView(ContentCreateView):
    model = Note


class ProjectCreateView(ContentCreateView):
    model = Project


class PostUpdateView(ContentUpdateView):
    model = Post


class NoteUpdateView(ContentUpdateView):
    model = Note


class ProjectUpdateView(ContentUpdateView):
    model = Project


class PostDownloadView(ContentDownloadView):
    model = Post


class NoteDownloadView(ContentDownloadView):
    model = Note


class ProjectDownloadView(ContentDownloadView):
    model = Project

