from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

class PDFGenerator:
    
    @staticmethod
    def generate_timetable_pdf(exam_schedules):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Examination Timetable", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Table data
        data = [['Subject Code', 'Subject Name', 'Date', 'Start Time', 'End Time', 'Hall']]
        
        for exam in exam_schedules:
            data.append([
                exam.subject.code,
                exam.subject.name,
                exam.exam_date.strftime('%Y-%m-%d'),
                exam.start_time.strftime('%H:%M'),
                exam.end_time.strftime('%H:%M'),
                exam.hall.name if exam.hall else 'TBA'
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_seating_pdf(seating_arrangements, exam_schedule):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"Seating Arrangement - {exam_schedule.subject.name}", styles['Title'])
        elements.append(title)
        
        subtitle = Paragraph(f"Date: {exam_schedule.exam_date} | Time: {exam_schedule.start_time} - {exam_schedule.end_time}", styles['Normal'])
        elements.append(subtitle)
        elements.append(Spacer(1, 0.3*inch))
        
        # Table data
        data = [['Roll Number', 'Student Name', 'Hall', 'Row', 'Column']]
        
        for arrangement in seating_arrangements:
            data.append([
                arrangement.student.roll_number,
                arrangement.student.user.get_full_name(),
                arrangement.hall.name,
                arrangement.seat_row,
                arrangement.seat_column
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        return buffer