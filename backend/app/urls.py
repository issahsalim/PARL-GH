from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('search/', views.search, name='search'),
    path("search/segment/<int:id>/", views.segment_detail, name="segment_detail"),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    
    # Summarization URLs
    path('summarize/', views.summarize_text, name='summarize_text'),
    path('summarize/segment/<int:segment_id>/', views.summarize_segment, name='summarize_segment'),
    path('summarize/session/<int:session_id>/', views.summarize_session, name='summarize_session'),
    path('summary/<int:summary_id>/', views.view_summary, name='view_summary'),
    path('summary/<int:summary_id>/json/', views.export_summary_json, name='export_summary_json'),
    path('summary/<int:summary_id>/csv/', views.export_summary_csv, name='export_summary_csv'),
    path('summaries/', views.summaries_list, name='summaries_list'),
    
    # API endpoints
    path('api/summarize/', views.api_quick_summary, name='api_quick_summary'),
    path('api/pipeline-status/', views.api_pipeline_status, name='api_pipeline_status'),
]

