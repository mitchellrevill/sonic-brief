import io
import csv
import logging
import tempfile
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)
from ...core.async_utils import run_sync
from ...core.dependencies import CosmosService


class ExportService:
    """Service for exporting user data and analytics to various formats"""
    
    def __init__(self, cosmos_service: CosmosService):
        self.cosmos_db = cosmos_service
        self.logger = logging.getLogger(__name__)

    async def export_users_csv(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Export all users to CSV format
        
        Args:
            filters: Optional filters to apply (permission, date_range, etc.)
            
        Returns:
            Dictionary with file path and metadata
        """
        try:
            # Get all users
            users = await self.cosmos_db.get_all_users()
            
            # Apply filters if provided
            if filters:
                users = self._apply_user_filters(users, filters)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.csv', 
                delete=False,
                newline='',
                encoding='utf-8'
            )
            
            # Write CSV data
            writer = csv.writer(temp_file)
            
            # Header row
            headers = [
                'ID', 'Email', 'Full Name', 'Permission', 'Source',
                'Microsoft OID', 'Tenant ID', 'Created At', 'Last Login',
                'Is Active', 'Permission Changed At', 'Permission Changed By'
            ]
            writer.writerow(headers)
            
            # Data rows
            for user in users:
                row = [
                    user.get('id', ''),
                    user.get('email', ''),
                    user.get('full_name', ''),
                    user.get('permission', ''),
                    user.get('source', ''),
                    user.get('microsoft_oid', ''),
                    user.get('tenant_id', ''),
                    user.get('created_at', ''),
                    user.get('last_login', ''),
                    str(user.get('is_active', False)),
                    user.get('permission_changed_at', ''),
                    user.get('permission_changed_by', '')
                ]
                writer.writerow(row)
            
            temp_file.close()
            
            # Generate filename
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f'sonic-brief-users-{timestamp}.csv'
            
            return {
                'status': 'success',
                'file_path': temp_file.name,
                'filename': filename,
                'record_count': len(users),
                'content_type': 'text/csv'
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting users to CSV: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def export_user_details_pdf(self, user_id: str, include_analytics: bool = True, days: int = 30) -> Dict[str, Any]:
        """
        Export individual user details to PDF format
        
        Args:
            user_id: ID of the user to export
            include_analytics: Whether to include analytics data
            
        Returns:
            Dictionary with file path and metadata
        """
        try:
            # Get user data
            user = await self.cosmos_db.get_user_by_id(user_id)
            if not user:
                return {
                    'status': 'error',
                    'message': 'User not found'
                }
            
            # Get analytics if requested
            analytics = None
            if include_analytics:
                # explicit package import
                from app.services.analytics.analytics_service import AnalyticsService
                analytics_service = AnalyticsService(self.cosmos_db)
                analytics_data = await analytics_service.get_user_analytics(user_id, days=days)
                analytics = analytics_data.get('analytics', {})
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.pdf', 
                delete=False
            )
            temp_file.close()
            
            # Create PDF
            doc = SimpleDocTemplate(
                temp_file.name,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Build PDF content
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                alignment=TA_CENTER,
                fontSize=18,
                spaceAfter=30
            )
            story.append(Paragraph("User Details Report", title_style))
            story.append(Spacer(1, 12))
            
            # User Information Section
            story.append(Paragraph("User Information", styles['Heading2']))
            
            user_data = [
                ['Field', 'Value'],
                ['User ID', user.get('id', 'N/A')],
                ['Email', user.get('email', 'N/A')],
                ['Full Name', user.get('full_name', 'N/A')],
                ['Permission Level', user.get('permission', 'N/A')],
                ['Account Source', user.get('source', 'N/A')],
                ['Microsoft OID', user.get('microsoft_oid', 'N/A')],
                ['Tenant ID', user.get('tenant_id', 'N/A')],
                ['Created At', self._format_datetime(user.get('created_at'))],
                ['Last Login', self._format_datetime(user.get('last_login'))],
                ['Is Active', 'Yes' if user.get('is_active') else 'No'],
                ['Permission Last Changed', self._format_datetime(user.get('permission_changed_at'))],
                ['Permission Changed By', user.get('permission_changed_by', 'N/A')],
            ]
            
            user_table = Table(user_data, colWidths=[2*inch, 4*inch])
            user_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            story.append(user_table)
            story.append(Spacer(1, 20))
            
            # Analytics Section
            if analytics:
                story.append(Paragraph(f"Analytics Summary (Last {days} Days)", styles['Heading2']))
                
                # Transcription Stats
                transcription_stats = analytics.get('transcription_stats', {})
                if transcription_stats:
                    story.append(Paragraph("Transcription Statistics", styles['Heading3']))
                    
                    transcription_data = [
                        ['Metric', 'Value'],
                        ['Total Transcription Minutes', f"{transcription_stats.get('total_minutes', 0):.1f}"],
                        ['Total Jobs', str(transcription_stats.get('total_jobs', 0))],
                        ['Average Job Duration (minutes)', f"{transcription_stats.get('average_job_duration', 0):.1f}"],
                    ]
                    
                    transcription_table = Table(transcription_data, colWidths=[3*inch, 2*inch])
                    transcription_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ]))
                    
                    story.append(transcription_table)
                    story.append(Spacer(1, 15))

                # Include detailed per-job minutes if available
                try:
                    # explicit package import
                    from app.services.analytics.analytics_service import AnalyticsService
                    analytics_service = AnalyticsService(self.cosmos_db)
                    minutes_data = await analytics_service.get_user_minutes_records(user.get('id'), days=30)
                    records = minutes_data.get('records', [])
                    if records:
                        story.append(Paragraph("Per-Job Duration Records", styles['Heading3']))
                        minutes_table_data = [["Job ID", "Timestamp", "Minutes", "File Name"]]
                        for r in records[:50]:  # cap rows to avoid huge PDFs
                            minutes_table_data.append([
                                r.get('job_id', ''),
                                self._format_datetime(r.get('timestamp')),
                                f"{float(r.get('audio_duration_minutes', 0.0)):.2f}",
                                r.get('file_name', '') or ''
                            ])
                        table = Table(minutes_table_data, colWidths=[2*inch, 2*inch, 1*inch, 2*inch])
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
                        ]))
                        story.append(table)
                        story.append(Spacer(1, 15))
                except Exception as e:
                    self.logger.warning(f"Could not include per-job minutes in PDF: {str(e)}")
                
                # Activity Stats
                activity_stats = analytics.get('activity_stats', {})
                if activity_stats:
                    story.append(Paragraph("Activity Statistics", styles['Heading3']))
                    
                    activity_data = [
                        ['Metric', 'Value'],
                        ['Total Events', str(activity_stats.get('total_events', 0))],
                        ['Login Count', str(activity_stats.get('login_count', 0))],
                        ['Jobs Created', str(activity_stats.get('jobs_created', 0))],
                        ['Last Activity', self._format_datetime(activity_stats.get('last_activity'))],
                    ]
                    
                    activity_table = Table(activity_data, colWidths=[3*inch, 2*inch])
                    activity_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ]))
                    
                    story.append(activity_table)
                    story.append(Spacer(1, 15))
            
            # Footer
            story.append(Spacer(1, 30))
            footer_text = f"Report generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            story.append(Paragraph(footer_text, styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            # Generate filename
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f'user-report-{user_id}-{timestamp}.pdf'
            
            return {
                'status': 'success',
                'file_path': temp_file.name,
                'filename': filename,
                'content_type': 'application/pdf'
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting user details to PDF: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def export_system_analytics_csv(self, days: int = 30) -> Dict[str, Any]:
        """Export system analytics (per-job minutes) within the last N days to CSV."""
        try:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=days)

            rows: List[List[str]] = []
            headers = [
                'job_id', 'user_id', 'timestamp', 'minutes', 'file_name', 'user_email'
            ]

            # Query analytics container for records in range
            query = (
                "SELECT c.id, c.job_id, c.user_id, c.timestamp, c.audio_duration_minutes, c.audio_duration_seconds, c.file_name "
                "FROM c WHERE c.timestamp >= @start AND c.timestamp <= @end"
            )
            params = [
                {"name": "@start", "value": start_dt.isoformat()},
                {"name": "@end", "value": end_dt.isoformat()},
            ]

            try:
                items = await run_sync(lambda: list(self.cosmos_db.analytics_container.query_items(
                    query=query, parameters=params, enable_cross_partition_query=True
                )))
                for it in items:
                    job_id = it.get('job_id') or it.get('id') or ''
                    user_id = it.get('user_id') or ''
                    ts = it.get('timestamp') or ''
                    minutes = it.get('audio_duration_minutes')
                    if minutes is None and it.get('audio_duration_seconds') is not None:
                        try:
                            minutes = float(it['audio_duration_seconds']) / 60.0
                        except Exception:
                            minutes = 0
                    try:
                        minutes_str = f"{float(minutes):.2f}" if minutes is not None else ""
                    except Exception:
                        minutes_str = ""
                    file_name = it.get('file_name') or ''
                    
                    # Get user email
                    user_email = ''
                    if user_id:
                        try:
                            user = await self.cosmos_db.get_user_by_id(user_id)
                            user_email = user.get('email', '') if user else ''
                        except Exception:
                            user_email = ''
                    
                    row = [str(job_id), str(user_id), str(ts), minutes_str, str(file_name), user_email]
                    rows.append(row)
            except Exception as qe:
                self.logger.error(f"Error querying analytics for export: {qe}")

            # Create temporary CSV file
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.csv', delete=False, newline='', encoding='utf-8'
            )
            writer = csv.writer(temp_file)
            writer.writerow(headers)
            for r in rows:
                writer.writerow(r)
            temp_file.close()

            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f'sonic-brief-system-analytics-{days}d-{timestamp}.csv'
            return {
                'status': 'success',
                'file_path': temp_file.name,
                'filename': filename,
                'record_count': len(rows),
                'content_type': 'text/csv'
            }
        except Exception as e:
            self.logger.error(f"Error exporting system analytics CSV: {e}")
            return {'status': 'error', 'message': str(e)}

    def _apply_user_filters(self, users: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filters to user list"""
        filtered_users = users
        
        # Filter by permission
        if 'permission' in filters and filters['permission']:
            filtered_users = [u for u in filtered_users if u.get('permission') == filters['permission']]
        
        # Filter by active status
        if 'is_active' in filters:
            filtered_users = [u for u in filtered_users if u.get('is_active') == filters['is_active']]
        
        # Filter by date range
        if 'date_range' in filters and filters['date_range']:
            date_range = filters['date_range']
            start_date = date_range.get('start')
            end_date = date_range.get('end')
            
            if start_date or end_date:
                filtered_users = self._filter_by_date_range(filtered_users, start_date, end_date)
        
        return filtered_users

    def _filter_by_date_range(self, users: List[Dict[str, Any]], start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Filter users by date range"""
        filtered = []
        
        for user in users:
            created_at = user.get('created_at')
            if not created_at:
                continue
                
            try:
                user_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                if start_date:
                    start_dt = datetime.fromisoformat(start_date)
                    if user_date < start_dt:
                        continue
                
                if end_date:
                    end_dt = datetime.fromisoformat(end_date)
                    if user_date > end_dt:
                        continue
                
                filtered.append(user)
                
            except:
                # Skip users with invalid dates
                continue
        
        return filtered

    def _format_datetime(self, dt_string: Optional[str]) -> str:
        """Format datetime string for display"""
        if not dt_string:
            return 'N/A'
        
        try:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return dt_string

    async def cleanup_temp_file(self, file_path: str):
        """Clean up temporary export file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                self.logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            self.logger.error(f"Error cleaning up temp file {file_path}: {str(e)}")
