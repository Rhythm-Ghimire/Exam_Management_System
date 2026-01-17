from ..models import SeatingArrangement
from collections import defaultdict


def generate_seating_arrangement(exam, students, halls):
    """
    Generate seating arrangement using Greedy Algorithm with alternate seating
    and Hash-Based Grouping for branch mixing
    """
    total_students = students.count()
    total_capacity = sum(hall.capacity for hall in halls)
    
    # Check if we have enough capacity (with alternate seating - 50% capacity)
    usable_capacity = total_capacity // 2
    if total_students > usable_capacity:
        return False
    
    # Group students by branch using hash map
    branch_groups = defaultdict(list)
    for student in students:
        branch_groups[student.branch].append(student)
    
    # Interleave students from different branches to avoid same-branch adjacency
    mixed_students = []
    branches = list(branch_groups.keys())
    
    while any(branch_groups.values()):
        for branch in branches:
            if branch_groups[branch]:
                mixed_students.append(branch_groups[branch].pop(0))
    
    # Assign students to halls with alternate seating (Greedy approach)
    student_index = 0
    
    for hall in halls:
        # Use alternate seats (1, 3, 5, 7... or even/odd pattern)
        max_seats = hall.capacity // 2  # Alternate seating
        seat_number = 1
        
        for _ in range(max_seats):
            if student_index >= len(mixed_students):
                break
            
            student = mixed_students[student_index]
            
            SeatingArrangement.objects.create(
                exam=exam,
                student=student,
                hall=hall,
                seat_number=seat_number
            )
            
            seat_number += 2  # Alternate seats: 1, 3, 5, 7...
            student_index += 1
        
        if student_index >= len(mixed_students):
            break
    
    return True