from django.contrib import admin
from .models import HansardFile, Session, Topic, Speaker, DebateSegment, Summary
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.html import format_html 
import os
import tempfile
import logging
from app.utils.pipeline import run_hansard_pipeline
from django.http import HttpResponseRedirect
from django.urls import path



# @admin.register(HansardFile)
# class HansardFileAdmin(admin.ModelAdmin):
#     list_display = ("file_name", "file_size", "date_downloaded")
#     search_fields = ("file_name",)
#     readonly_fields = ("file_size", "date_downloaded")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("title", "sitting_date", "pdf_file_link")
    search_fields = ("title",)
    list_filter = ("sitting_date",)

    @admin.display(description="PDF")
    def pdf_file_link(self, obj):
        if not obj.pdf_file:
            return "-"
        # prefer a stored file URL if available
        file_field = getattr(obj.pdf_file, "file", None)
        file_name = getattr(obj.pdf_file, "file_name", None) or getattr(obj.pdf_file, "name", None)
        if file_field and getattr(file_field, "url", None):
            return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', file_field.url, file_name or file_field.name)
        return file_name or "-"


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ("name", "role")
    search_fields = ("name",)


@admin.register(DebateSegment)
class DebateSegmentAdmin(admin.ModelAdmin):
    list_display = ("short_text", "speaker", "session")
    search_fields = ("text", "speaker__name")
    list_filter = ("session", "speaker")

    def short_text(self, obj):
        return obj.text[:120] + ("..." if len(obj.text) > 120 else "")

    @admin.display(description="Debate Text")
    def short_text(self, obj):
        return obj.text[:120] + ("..." if len(obj.text) > 120 else "")


# uploading pdf
from .forms import PDFUploadForm
from .utils.hansard_pipeline import process_pdf

logger = logging.getLogger(__name__)


@admin.register(HansardFile)
class HansardAdmin(admin.ModelAdmin):
    change_list_template = "admin/hansard_upload.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("upload/", self.admin_site.admin_view(self.upload_pdf), name="hansard_upload"),
        ] 
        return custom + urls
    
    list_display = ("file_name", "file_size", "date_downloaded")
    actions = ["run_pipeline_action"]

    def run_pipeline_action(self, request, queryset):
        """Execute the hansard pipeline for selected files only"""
        if not queryset.exists():
            self.message_user(request, "No files selected.", level=messages.WARNING)
            return
        
        from app.utils.pipeline import process_pdf
        processed = 0
        errors = []
        
        for hansard in queryset:
            if not os.path.exists(hansard.file_path):
                errors.append(f"{hansard.file_name}: File not found at {hansard.file_path}")
                continue
            
            try:
                process_pdf(hansard)
                processed += 1
                print(f"✅ Processed: {hansard.file_name}")
            except Exception as e:
                error_msg = str(e)
                errors.append(f"{hansard.file_name}: {error_msg}")
                print(f"❌ Error processing {hansard.file_name}: {error_msg}")
        
        # Show results
        if processed > 0:
            msg = f"✅ Successfully processed {processed} file(s)."
            if errors:
                msg += f"\n⚠️ Errors ({len(errors)}): " + "; ".join(errors[:3])
            self.message_user(request, msg, level=messages.SUCCESS)
        else:
            msg = f"❌ No files processed. Errors: " + "; ".join(errors[:3])
            self.message_user(request, msg, level=messages.ERROR)

    run_pipeline_action.short_description = "Run Hansard Pipeline (Selected Files)"


    def upload_pdf(self, request):
        form = PDFUploadForm(request.POST or None, request.FILES or None)

        if request.method == "POST" and form.is_valid():
            file = request.FILES["pdf_file"]

            if not file.name.lower().endswith(".pdf"):
                messages.error(request, "Only PDF files are allowed.")
                return redirect(request.path)

            # Save file permanently
            upload_dir = "ghana_hansards"
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, file.name)

            if os.path.exists(file_path):
                messages.warning(request, "This PDF already exists.")
            else: 
                with open(file_path, "wb") as f:
                    for chunk in file.chunks():
                        f.write(chunk)

                HansardFile.objects.create(
                    file_name=file.name,
                    file_path=file_path.replace("\\", "/"),
                    file_size=file.size
                )

            # 🚀 RUN PIPELINE with error handling
            result = run_hansard_pipeline()
            
            if result.get('success', False):
                messages.success(
                    request,
                    f"✅ PDF uploaded and processed successfully. {result.get('message', '')}"
                )
            else:
                # Show warning instead of error since file was still uploaded
                messages.warning(
                    request,
                    f"⚠️ PDF uploaded but pipeline encountered an issue: {result.get('message', 'Unknown error')}"
                )

            app_label = HansardFile._meta.app_label
            model_name = HansardFile._meta.model_name
            return redirect(f"/admin/{app_label}/{model_name}/")

        return render(request, "admin/upload_form.html", {"form": form})

# ============ SUMMARY ADMIN ============

@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    list_display = ("get_title", "content_type", "get_stats", "created_by", "created_at")
    list_filter = ("content_type", "created_at", "session")
    search_fields = ("summary_text", "original_text", "created_by")
    readonly_fields = ("original_text", "summary_text", "speakers_mentioned", "motions", 
                       "outcomes", "original_word_count", "summary_word_count", "reduction_percentage", 
                       "created_at", "updated_at")
    
    fieldsets = (
        ("Summary Information", {
            'fields': ('content_type', 'created_by', 'created_at', 'updated_at')
        }),
        ("Related Content", {
            'fields': ('session', 'topic', 'debate_segment')
        }),
        ("Content", {
            'fields': ('original_text', 'summary_text'),
            'classes': ('collapse',)
        }),
        ("Extracted Information", {
            'fields': ('speakers_mentioned', 'motions', 'outcomes')
        }),
        ("Statistics", {
            'fields': ('original_word_count', 'summary_word_count', 'reduction_percentage')
        })
    )
    
    def get_title(self, obj):
        if obj.session:
            return f"Summary of {obj.session.title}"
        elif obj.debate_segment:
            return f"Summary of {obj.debate_segment.speaker.name}'s segment"
        else:
            return "Custom Text Summary"
    get_title.short_description = "Title"
    
    def get_stats(self, obj):
        reduction = f"{obj.reduction_percentage:.1f}%"
        return format_html(
            '<span style="background: #e3f2fd; padding: 5px 10px; border-radius: 4px;">{} → {} ({})</span>',
            obj.original_word_count,
            obj.summary_word_count,
            reduction
        )
    get_stats.short_description = "Word Count Reduction"
    
    def has_add_permission(self, request):
        # Summaries are created via views, not admin
        return False