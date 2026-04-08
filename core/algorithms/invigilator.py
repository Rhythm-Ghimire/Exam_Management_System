from ..models import InvigilatorAssignment, Exam
from collections import defaultdict


def assign_invigilators(exam, halls, invigilators):
   
    invigilator_list = list(invigilators)
    if not invigilator_list:
        return False

    # Find halls actually used by this exam
    from ..models import SeatingArrangement
    used_hall_ids = SeatingArrangement.objects.filter(exam=exam).values_list('hall_id', flat=True).distinct()
    halls_needed = [h for h in halls if h.id in used_hall_ids]
    if not halls_needed:
        return False

    # --- Build context for this date ---
    # How many duties each invigilator already has today
    duties_today = defaultdict(int)
    # Which hall each invigilator was in yesterday (for rotation)
    hall_yesterday = defaultdict(set)

    same_day_exams = Exam.objects.filter(date=exam.date).exclude(id=exam.id)
    for e in same_day_exams:
        for a in InvigilatorAssignment.objects.filter(exam=e):
            duties_today[a.invigilator.id] += 1

    # Look at assignments from any exam the day before
    from datetime import timedelta
    yesterday = exam.date - timedelta(days=1)
    prev_day_exams = Exam.objects.filter(date=yesterday)
    for e in prev_day_exams:
        for a in InvigilatorAssignment.objects.filter(exam=e):
            hall_yesterday[a.invigilator.id].add(a.hall.id)

    # Sort invigilators by fewest duties today first (fairness)
    def sort_key(inv):
        return duties_today[inv.id]

    sorted_invigs = sorted(invigilator_list, key=sort_key)

    assignments = []

    def backtrack(hall_idx, used_ids):
        if hall_idx >= len(halls_needed):
            return True

        hall = halls_needed[hall_idx]

        for inv in sorted_invigs:
            if inv.id in used_ids:
                continue
            if duties_today[inv.id] >= 2:
                continue
            # Prefer not putting same invigilator in same hall as yesterday
            # (soft constraint — only skip if there's another option)
            was_here_yesterday = hall.id in hall_yesterday.get(inv.id, set())
            if was_here_yesterday and len(sorted_invigs) > len(halls_needed):
                continue  # skip only if we have enough invigilators to avoid it

            assignments.append({'exam': exam, 'invigilator': inv, 'hall': hall})
            used_ids.add(inv.id)
            duties_today[inv.id] += 1

            if backtrack(hall_idx + 1, used_ids):
                return True

            assignments.pop()
            used_ids.remove(inv.id)
            duties_today[inv.id] -= 1

        # Retry without the rotation constraint if we get stuck
        for inv in sorted_invigs:
            if inv.id in used_ids:
                continue
            if duties_today[inv.id] >= 2:
                continue

            assignments.append({'exam': exam, 'invigilator': inv, 'hall': hall})
            used_ids.add(inv.id)
            duties_today[inv.id] += 1

            if backtrack(hall_idx + 1, used_ids):
                return True

            assignments.pop()
            used_ids.remove(inv.id)
            duties_today[inv.id] -= 1

        return False

    success = backtrack(0, set())

    if success:
        for a in assignments:
            InvigilatorAssignment.objects.create(**a)
        return True

    # --- Greedy fallback with rotation ---
    # Cycle through invigilators, preferring those who weren't in that hall yesterday
    used_ids = set()
    inv_cycle = list(sorted_invigs)
    idx = 0
    for hall in halls_needed:
        # Try to find someone who wasn't in this hall yesterday
        assigned = False
        for attempt in range(len(inv_cycle)):
            inv = inv_cycle[(idx + attempt) % len(inv_cycle)]
            if inv.id in used_ids:
                continue
            if hall.id in hall_yesterday.get(inv.id, set()):
                continue
            InvigilatorAssignment.objects.create(exam=exam, invigilator=inv, hall=hall)
            used_ids.add(inv.id)
            idx = (idx + attempt + 1) % len(inv_cycle)
            assigned = True
            break

        if not assigned:
            # Just pick anyone available
            for attempt in range(len(inv_cycle)):
                inv = inv_cycle[(idx + attempt) % len(inv_cycle)]
                if inv.id not in used_ids:
                    InvigilatorAssignment.objects.create(exam=exam, invigilator=inv, hall=hall)
                    used_ids.add(inv.id)
                    idx = (idx + attempt + 1) % len(inv_cycle)
                    break

    return True