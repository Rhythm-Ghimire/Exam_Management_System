from ..models import SeatingArrangement


def generate_seating_arrangement(exam, students, halls):
    
    student_list = list(students.order_by('branch', 'semester', 'roll_number'))
    total_students = len(student_list)
    
    if total_students == 0:
        return False
    
    # Get available halls sorted by name
    available_halls = list(halls.filter(is_available=True).order_by('name'))
    
    if not available_halls:
        return False
    
    # Group students by branch_semester
    from collections import defaultdict
    student_groups = defaultdict(list)
    for student in student_list:
        key = f"{student.branch}_sem{student.semester}"
        student_groups[key].append(student)
    
    # Check if all students are same group
    if len(student_groups) == 1:
        # Same branch+semester - sequential by roll number
        return assign_single_group_sequential(exam, student_list, available_halls)
    else:
        # Mixed groups - pair different groups
        return assign_mixed_groups_paired(exam, student_list, available_halls, student_groups)


def assign_single_group_sequential(exam, students, halls):
   
    student_index = 0
    hall_index = 0
    
    while student_index < len(students) and hall_index < len(halls):
        hall = halls[hall_index]
        num_benches = hall.capacity // 2
        
        # Fill this hall - one student per bench
        for bench_num in range(1, num_benches + 1):
            if student_index >= len(students):
                break
            
            SeatingArrangement.objects.create(
                exam=exam,
                student=students[student_index],
                hall=hall,
                seat_number=bench_num
            )
            student_index += 1
        
        # Move to next hall
        hall_index += 1
    
    return student_index == len(students)


def assign_mixed_groups_paired(exam, students, halls, student_groups):
    
    # Interleave students from different groups
    group_keys = list(student_groups.keys())
    max_length = max(len(group) for group in student_groups.values())
    
    mixed_students = []
    for i in range(max_length):
        for key in group_keys:
            if i < len(student_groups[key]):
                mixed_students.append(student_groups[key][i])
    
    student_index = 0
    hall_index = 0
    
    while student_index < len(mixed_students) and hall_index < len(halls):
        hall = halls[hall_index]
        num_benches = hall.capacity // 2
        
        # Fill this hall
        for bench_num in range(1, num_benches + 1):
            if student_index >= len(mixed_students):
                break
            
            # First student on bench
            student1 = mixed_students[student_index]
            SeatingArrangement.objects.create(
                exam=exam,
                student=student1,
                hall=hall,
                seat_number=bench_num
            )
            student_index += 1
            
            # Try to add second student
            if student_index < len(mixed_students):
                student2 = mixed_students[student_index]
                
                # Check if different group
                can_pair = (student1.branch != student2.branch or 
                           student1.semester != student2.semester)
                
                if can_pair:
                    # Same bench
                    SeatingArrangement.objects.create(
                        exam=exam,
                        student=student2,
                        hall=hall,
                        seat_number=bench_num
                    )
                    student_index += 1
                # If can't pair, student2 goes to next bench (don't increment here)
        
        # Move to next hall
        hall_index += 1
    
    return student_index == len(mixed_students)