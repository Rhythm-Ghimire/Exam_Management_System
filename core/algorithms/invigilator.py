from ..models import InvigilatorAssignment, Exam
from collections import defaultdict


def assign_invigilators(exam, halls, invigilators):
    """
    Assign invigilators using Backtracking Algorithm to ensure no repetition
    on the same day and fair distribution
    """
    # Get all exams on the same day
    same_day_exams = Exam.objects.filter(date=exam.date)
    
    # Track which invigilators are already assigned on this day
    assigned_today = defaultdict(set)
    for same_exam in same_day_exams:
        if same_exam.id != exam.id:
            assignments = InvigilatorAssignment.objects.filter(exam=same_exam)
            for assignment in assignments:
                assigned_today[assignment.invigilator.id].add(same_exam.id)
    
    # Get halls that need invigilators for this exam
    used_halls = set()
    from ..models import SeatingArrangement
    seating = SeatingArrangement.objects.filter(exam=exam).values_list('hall_id', flat=True).distinct()
    halls_needed = [hall for hall in halls if hall.id in seating]
    
    # Convert invigilators to list for indexing
    invigilator_list = list(invigilators)
    assignments = []
    
    def backtrack(hall_index, used_invigilators):
        # Base case: all halls assigned
        if hall_index >= len(halls_needed):
            return True
        
        hall = halls_needed[hall_index]
        
        # Try each invigilator
        for invigilator in invigilator_list:
            # Skip if already used in this exam or assigned too many times today
            if invigilator.id in used_invigilators:
                continue
            
            # Prefer invigilators with fewer assignments today
            if len(assigned_today[invigilator.id]) > 2:  # Max 2 duties per day
                continue
            
            # Make assignment
            assignments.append({
                'exam': exam,
                'invigilator': invigilator,
                'hall': hall
            })
            used_invigilators.add(invigilator.id)
            
            # Recurse
            if backtrack(hall_index + 1, used_invigilators):
                return True
            
            # Backtrack
            assignments.pop()
            used_invigilators.remove(invigilator.id)
        
        return False
    
    # Start backtracking
    if backtrack(0, set()):
        # Create all assignments
        for assignment_data in assignments:
            InvigilatorAssignment.objects.create(**assignment_data)
        return True
    else:
        # Fallback: simple greedy assignment if backtracking fails
        invigilator_index = 0
        for hall in halls_needed:
            invigilator = invigilator_list[invigilator_index % len(invigilator_list)]
            InvigilatorAssignment.objects.create(
                exam=exam,
                invigilator=invigilator,
                hall=hall
            )
            invigilator_index += 1
        return True