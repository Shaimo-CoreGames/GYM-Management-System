from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from .models import *
import datetime
from datetime import timedelta

ADMIN_CREDENTIALS = {
    'username': 'admin',
    'password': 'admin123',
    'first_name': 'Admin',
    'last_name': 'User',
    'email': 'admin@gym.com',
    'phone_number': '03001234567'
}

DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def home(request):
    return render(request, 'home.html')

def user_login(request):
    data = {}
    if request.method == "POST":
        username = request.POST.get("u_username")
        password = request.POST.get("u_password")
        user_data = Gym_user.get_user_by_username(username)
        
        if user_data:
            if check_password(password, user_data.password):
                if not user_data.is_approved:
                    data["error"] = "Your account is pending admin approval."
                elif user_data.membership_end_date and user_data.membership_end_date < datetime.date.today():
                    if not user_data.is_blocked:
                        user_data.is_blocked = True
                        user_data.save()
                    data["error"] = "Your membership has expired! Please renew your membership to continue."
                elif user_data.is_blocked:
                    data["error"] = "Your membership has expired! Please renew your membership to continue."
                else:
                    request.session['user_id'] = user_data.id
                    request.session['user_type'] = 'member'
                    return redirect('/user_portal')
            else:
                data["error"] = "Password is incorrect!"
        else:
            data["error"] = "Incorrect username or password!"
    
    return render(request, 'user_login.html', data)

def trainer_login(request):
    data = {}
    if request.method == "POST":
        username = request.POST.get("t_username")
        password = request.POST.get("t_password")
        trainer_data = Trainer.get_trainer_by_username(username)
        
        if trainer_data:
            if check_password(password, trainer_data.password):
                request.session['trainer_id'] = trainer_data.id
                request.session['user_type'] = 'trainer'
                return redirect('/trainer_portal')
            else:
                data["error"] = "Password is incorrect!"
        else:
            data["error"] = "Incorrect username or password!"
    
    return render(request, 'trainer_login.html', data)

def admin_login(request):
    data = {}
    if request.method == "POST":
        username = request.POST.get("a_username")
        password = request.POST.get("a_password")
        
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            request.session['admin_logged_in'] = True
            request.session['user_type'] = 'admin'
            return redirect('/admin_portal')
        else:
            data["error"] = "Incorrect username or password!"
    
    return render(request, 'admin_login.html', data)

def logout(request):
    request.session.flush()
    return redirect('/')

def new_registration(request):
    data = {}
    membership_plans = MembershipPlan.objects.all()
    genders = Gender.objects.all()
    data['membership_plans'] = membership_plans
    data['genders'] = genders
    
    if request.method == "POST":
        first_name = request.POST.get("firstname")
        last_name = request.POST.get("lastname")
        dob = request.POST.get("dob")
        phone_number = request.POST.get("phone_number")
        username = request.POST.get("username")
        password = request.POST.get("password")
        c_password = request.POST.get("c_password")
        gender_id = request.POST.get("gender")
        email = request.POST.get("email")
        membership_plan_id = request.POST.get("membership_plan")
        payment_proof = request.FILES.get("payment_proof")
        
        error = ""
        
        if len(first_name) < 2 or len(last_name) < 2 or len(username) < 2:
            error = "Name and username fields cannot be empty"
        elif len(password) < 5:
            error = "Password length should be at least 5 characters"
        elif password != c_password:
            error = "Both passwords should match"
        elif Gym_user.get_user_by_username(username):
            error = "Username already exists"
        elif not payment_proof:
            error = "Please upload payment proof"
        else:
            user = Gym_user()
            user.first_name = first_name.strip()
            user.last_name = last_name.strip()
            user.dob = dob
            user.phone_number = phone_number
            user.username = username.strip()
            user.password = make_password(password)
            user.email = email
            user.gender_id = gender_id
            user.membership_plan_id = membership_plan_id
            user.payment_proof = payment_proof
            user.is_approved = False
            user.save()
            
            data["msg"] = "Registration successful! Please wait for admin approval (within 24 hours)."
            data["success"] = True
        
        data["error"] = error
    
    return render(request, 'new_registration.html', data)

def user_portal(request):
    if 'user_id' not in request.session:
        return redirect('/user_login')
    
    user = Gym_user.get_user_by_id(request.session['user_id'])
    
    bmi = None
    bmi_status = None
    if user.height and user.weight:
        height_m = user.height / 100
        bmi = round(user.weight / (height_m ** 2), 2)
        if bmi < 18.5:
            bmi_status = "Underweight"
        elif bmi < 25:
            bmi_status = "Normal weight"
        elif bmi < 30:
            bmi_status = "Overweight"
        else:
            bmi_status = "Obese"
    
    all_workout_plans = WorkoutPlan.objects.all()
    all_diet_plans = DietPlan.objects.all()
    
    data = {
        'user': user,
        'bmi': bmi,
        'bmi_status': bmi_status,
        'all_workout_plans': all_workout_plans,
        'all_diet_plans': all_diet_plans
    }
    
    return render(request, 'user_portal.html', data)

def request_trainer(request):
    if 'user_id' not in request.session:
        return redirect('/user_login')
    
    user = Gym_user.get_user_by_id(request.session['user_id'])
    user.trainer_requested = True
    user.save()
    
    return redirect('/user_portal')

def update_user_info(request):
    if 'user_id' not in request.session:
        return redirect('/user_login')
    
    if request.method == "POST":
        user = Gym_user.get_user_by_id(request.session['user_id'])
        user.email = request.POST.get("email", user.email)
        user.phone_number = request.POST.get("phone_number", user.phone_number)
        user.weight = request.POST.get("weight", user.weight)
        user.height = request.POST.get("height", user.height)
        user.save()
    
    return redirect('/user_portal')

def trainer_portal(request):
    if 'trainer_id' not in request.session:
        return redirect('/trainer_login')
    
    trainer = Trainer.objects.get(id=request.session['trainer_id'])
    workout_plans = WorkoutPlan.objects.filter(trainer=trainer).prefetch_related('workout_days')
    diet_plans = DietPlan.objects.filter(trainer=trainer).prefetch_related('diet_days')
    assigned_members = Gym_user.objects.filter(assigned_trainer=trainer)
    
    data = {
        'trainer': trainer,
        'workout_plans': workout_plans,
        'diet_plans': diet_plans,
        'assigned_members': assigned_members,
        'days_of_week': DAYS_OF_WEEK
    }
    
    return render(request, 'trainer_portal.html', data)

def create_workout_plan(request):
    if 'trainer_id' not in request.session:
        return redirect('/trainer_login')
    
    if request.method == "POST":
        trainer = Trainer.objects.get(id=request.session['trainer_id'])
        
        # Create workout plan
        workout = WorkoutPlan()
        workout.trainer = trainer
        workout.name = request.POST.get("name")
        workout.description = request.POST.get("description")
        workout.difficulty_level = request.POST.get("difficulty_level")
        workout.save()
        
        # Create workout days
        for day in DAYS_OF_WEEK:
            exercises = request.POST.get(f"exercises_{day}")
            if exercises and exercises.strip():
                WorkoutDay.objects.create(
                    workout_plan=workout,
                    day_name=day,
                    exercises=exercises,
                    notes=request.POST.get(f"notes_{day}", "")
                )
    
    return redirect('/trainer_portal')

def create_diet_plan(request):
    if 'trainer_id' not in request.session:
        return redirect('/trainer_login')
    
    if request.method == "POST":
        trainer = Trainer.objects.get(id=request.session['trainer_id'])
        
        # Create diet plan
        diet = DietPlan()
        diet.trainer = trainer
        diet.name = request.POST.get("name")
        diet.description = request.POST.get("description")
        diet.total_calories = request.POST.get("total_calories")
        diet.save()
        
        # Create diet days
        for day in DAYS_OF_WEEK:
            breakfast = request.POST.get(f"breakfast_{day}")
            if breakfast and breakfast.strip():
                DietDay.objects.create(
                    diet_plan=diet,
                    day_name=day,
                    breakfast=breakfast,
                    lunch=request.POST.get(f"lunch_{day}", ""),
                    dinner=request.POST.get(f"dinner_{day}", ""),
                    snacks=request.POST.get(f"snacks_{day}", "")
                )
    
    return redirect('/trainer_portal')

def assign_plan_to_member(request):
    if 'trainer_id' not in request.session:
        return redirect('/trainer_login')
    
    if request.method == "POST":
        member_id = request.POST.get("member_id")
        workout_plan_id = request.POST.get("workout_plan_id")
        diet_plan_id = request.POST.get("diet_plan_id")
        
        if member_id:
            try:
                member = Gym_user.objects.get(id=member_id)
                
                if workout_plan_id:
                    member.assigned_workout_plan_id = workout_plan_id
                if diet_plan_id:
                    member.assigned_diet_plan_id = diet_plan_id
                
                member.save()
            except Gym_user.DoesNotExist:
                pass
    
    return redirect('/trainer_portal')

def admin_portal(request):
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    pending_approvals = Gym_user.get_pending_approvals()
    trainer_requests = Gym_user.get_trainer_requests()
    all_members = Gym_user.objects.filter(is_approved=True)
    all_trainers = Trainer.objects.all()
    
    total_revenue = sum([member.membership_plan.price for member in all_members if member.membership_plan])
    
    data = {
        'admin': ADMIN_CREDENTIALS,
        'pending_approvals': pending_approvals,
        'trainer_requests': trainer_requests,
        'all_members': all_members,
        'all_trainers': all_trainers,
        'total_revenue': total_revenue
    }
    
    return render(request, 'admin_portal.html', data)

def userdetails(request):
    u_id = request.GET.get('u_id')

    if u_id:
        try:
            user = Gym_user.objects.get(id=int(u_id))
        except Gym_user.DoesNotExist:
            return HttpResponse("User not found")

        return render(request, 'userdetails.html', {'user': user})
    else:
        return HttpResponse("No user ID provided")




def approve_payment(request, user_id):
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    user = Gym_user.objects.get(id=user_id)
    user.is_approved = True
    user.is_blocked = False
    user.reminder_sent = False
    user.membership_start_date = datetime.date.today()
    user.membership_end_date = datetime.date.today() + timedelta(days=user.membership_plan.duration_months * 30)
    user.save()
    
    return redirect('/admin_portal')

def reject_payment(request, user_id):
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    user = Gym_user.objects.get(id=user_id)
    user.delete()
    
    return redirect('/admin_portal')

def create_trainer(request):
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    if request.method == "POST":
        trainer = Trainer()
        trainer.first_name = request.POST.get("first_name")
        trainer.last_name = request.POST.get("last_name")
        trainer.email = request.POST.get("email")
        trainer.phone_number = request.POST.get("phone_number")
        trainer.username = request.POST.get("username")
        trainer.password = make_password(request.POST.get("password"))
        trainer.specialization = request.POST.get("specialization")
        trainer.save()
    
    return redirect('/admin_portal')

def assign_trainer_to_member(request):
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    if request.method == "POST":
        member_id = request.POST.get("member_id")
        trainer_id = request.POST.get("trainer_id")
        
        member = Gym_user.objects.get(id=member_id)
        member.assigned_trainer_id = trainer_id
        member.trainer_requested = False
        member.save()
    
    return redirect('/admin_portal')

def trainer_attendance(request):
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    trainers = Trainer.objects.all()
    today = datetime.date.today()
    
    if request.method == "POST":
        for trainer in trainers:
            present = request.POST.get(f"trainer_{trainer.id}")
            if present:
                TrainerAttendance.objects.update_or_create(
                    trainer=trainer,
                    date=today,
                    defaults={'present': True}
                )
    
    attendance_records = TrainerAttendance.objects.filter(date=today)
    
    data = {
        'trainers': trainers,
        'attendance_records': attendance_records,
        'today': today
    }
    
    return render(request, 'trainer_attendance.html', data)

def delete_user(request, u_id):
    try:
        user = Gym_user.objects.get(id=u_id)
        user.delete()
        return redirect("all_members")
    except Gym_user.DoesNotExist:
        return HttpResponse("User not found", status=404)



def delete_profbyuser(request):
    user_id=request.GET.get("u_id")
    user_=Gym_user.objects.get(id=user_id)
    user_.delete()
    return redirect("/")

def search_members(request):
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    query = request.GET.get('q', '')
    members = Gym_user.objects.filter(
        first_name__icontains=query
    ) | Gym_user.objects.filter(
        last_name__icontains=query
    ) | Gym_user.objects.filter(
        username__icontains=query
    )
    
    data = {
        'members': members,
        'query': query
    }
    
    return render(request, 'search_results.html', data)
def contact_us(request):
    return render(request, 'contact.html')

def workout_plan(request):
    id_ = request.GET.get("pid")
    user = Gym_user.get_user_by_id(int(id_))
    data={}
    data['user']=user
    today = datetime.datetime.now()
    data['today']=today.strftime("%A")
    return render(request, 'workout_plan.html', data)


def workout(request):
    id_ = request.GET.get("pid")
    user = Gym_user.get_user_by_id(int(id_))
    data={}
    data['user']=user
    today_ = datetime.datetime.now()
    today=today_.weekday()
    data['today']=today_.strftime("%A")
    date_time_=user.date_of_joining
    year = int(date_time_.year)
    month = int(date_time_.month)
    day = int(date_time_.day)

    date_ = datetime.datetime(year, month, day)
    joining_day = date_.strftime('%A')
    split_ = user.gym_split_id
    print(split_, type(split_), joining_day)
    splits_1 = ["chest", "back", "shoulder", "bicep_tricep", "leg", "rest", "chest", "back", "shoulder", "bicep_tricep", "leg", "rest"]
    splits_2 = ["push", "pull", "leg", "push", "pull", "leg", "push", "pull", "leg", "push", "pull", "leg"]
    if split_ == 1:
        if joining_day == 'Monday':
            exercise = splits_1[6 + today]
            data['exercise'] = exercise
        if joining_day == 'Tuesday':
            exercise = splits_1[5 + today]
            data['exercise'] = exercise
        if joining_day == 'Wednesday':
            exercise = splits_1[4 + today]
            data['exercise'] = exercise
        if joining_day == 'Thursday':
            exercise = splits_1[3 + today]
            data['exercise'] = exercise
        if joining_day == 'Friday':
            exercise = splits_1[2 + today]
            print(exercise)
            data['exercise'] = exercise
        if joining_day == 'Saturday':
            exercise = splits_1[1 + today]
            data['exercise'] = exercise
    if split_ == 2:
        if joining_day == 'Monday':
            exercise = splits_2[6 + today]
            data['exercise'] = exercise
        elif joining_day == 'Tuesday':
            exercise = splits_2[5 + today]
            data['exercise'] = exercise
        elif joining_day == 'Wednesday':
            exercise = splits_2[4 + today]
            data['exercise'] = exercise
        elif joining_day == 'Thursday':
            exercise = splits_2[3 + today]
            data['exercise'] = exercise
        elif joining_day == 'Friday':
            exercise = splits_2[2 + today]
            data['exercise'] = exercise
        elif joining_day == 'Saturday':
            exercise = splits_2[1 + today]
            data['exercise'] = exercise

    return render(request, 'workout.html', data)
def diet_plan(request):
    return render(request, 'diet_plan.html')

def admin_login(request):
    data={}
    if request.method=="POST":
        username = request.POST.get("a_username")
        password = request.POST.get("a_password")
        error = "" 
        
        # Check against hardcoded credentials
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            # Set session to mark admin as logged in
            request.session['admin_logged_in'] = True
            request.session['admin_username'] = username
            
            # data["admin"] = ADMIN_CREDENTIALS.copy()
            return redirect("admin_portal")
        else:
            error = "Incorrect Username or password!"
            data["error"] = error
            return render(request, 'admin_login.html', data)
    else:
        return render(request, 'admin_login.html', data)

def admin_portal(request):
    # Check if admin is logged in via session
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    # Pass hardcoded admin data to template
    admin_data = ADMIN_CREDENTIALS.copy()
    return render(request, 'admin_portal.html', {'admin': admin_data})

def all_members(request):
    members = Gym_user.get_all_users()
    return render(request, 'all_members.html', {'users': members})



def admin_logout(request):
    # Clear admin session
    if 'admin_logged_in' in request.session:
        del request.session['admin_logged_in']
    if 'admin_username' in request.session:
        del request.session['admin_username']
    return redirect('/')





# @csrf_exempt
# @require_POST
def upload_profile_image(request):
    try:
        # Get user ID from POST data or GET parameter
        user_id = request.POST.get('user_id') or request.GET.get('u_id')
        
        if not user_id:
            return JsonResponse({'success': False, 'message': 'User ID is required.'})
        
        # Get the user
        user = Gym_user.objects.get(id=int(user_id))
        
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return JsonResponse({'success': False, 'message': 'Invalid file type. Please upload JPEG, PNG, GIF, or WebP images.'})
            
            # Validate file size (5MB limit)
            if image_file.size > 5 * 1024 * 1024:
                return JsonResponse({'success': False, 'message': 'File too large. Please upload images smaller than 5MB.'})
            
            # Delete old image if it exists and is not the default
            if user.image and user.image.name != "users_profile_images/image.png":
                try:
                    user.image.delete(save=False)
                except:
                    pass  # Ignore if file doesn't exist
            
            # Save the new image
            user.image.save(image_file.name, image_file, save=True)
            
            return JsonResponse({
                'success': True, 
                'message': 'Profile picture updated successfully!',
                'image_url': user.image.url
            })
        else:
            return JsonResponse({'success': False, 'message': 'No image file provided.'})
            
    except Gym_user.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User does not exist.'})
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid user ID format.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})



def change_admin_password(request):   
    global ADMIN_CREDENTIALS
    data={}
    msg=""
    
    # Check if admin is logged in
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    if request.method=="GET":
        # Pass current admin data to template
        data["admin"] = ADMIN_CREDENTIALS.copy()
        return render(request, 'change_admin_password.html', data)
    
    if request.method=="POST":
        new_password = request.POST.get("n_pass")
        # Update the hardcoded password
        ADMIN_CREDENTIALS['password'] = new_password
        msg = "Password Has Changed Successfully!"
        data["msg"] = msg
        data["admin"] = ADMIN_CREDENTIALS.copy()
        return render(request, 'change_admin_password.html', data)

def take_attendance(request):
    ids=[]
    if request.method=="GET":
        return render(request, 'take_attendance.html')
    else:
        ids.append(request.POST.get("1"))
        ids.append(request.POST.get("2"))
        ids.append(request.POST.get("3"))
        ids.append(request.POST.get("4"))
        ids.append(request.POST.get("5"))
        
        for i in range(5):
            try:
                user = Gym_user.get_user_by_id(ids[i])
                user.no_of_days += 1 
                user.save()
            except Gym_user.DoesNotExist:            
                continue
        data={}
        data['msg']="Successfully updated the attendance!"
        return render(request, 'take_attendance.html', data)    

def change_user_password(request):
    data={}
    msg=""  
    id_= request.GET.get("u_id")
    if request.method=="GET":
        user=Gym_user.objects.get(pk=id_)    
        data["user"]=user
        return render(request, 'change_user_password.html', data)
    if request.method=="POST":
        user_id=request.POST.get("user_id")
        n_password=request.POST.get("n_pass")
        user_data = Gym_user.objects.get(id=user_id)
        user_data.password=n_password
        user_data.save()
        msg="Password Has Changed Successfully!"
        data["msg"] = msg
        return render(request, 'change_user_password.html', data)


def attendance_history(request):
    if 'admin_logged_in' not in request.session:
        return redirect('/admin_login')
    
    trainers = Trainer.objects.all()
    
    # Get all attendance records ordered by date (most recent first)
    all_attendance = TrainerAttendance.objects.all().order_by('-date')
    
    # Optional: Filter by trainer if provided
    trainer_filter = request.GET.get('trainer_id')
    if trainer_filter:
        all_attendance = all_attendance.filter(trainer_id=trainer_filter)
    
    data = {
        'trainers': trainers,
        'attendance_records': all_attendance,
        'selected_trainer': trainer_filter
    }
    
    return render(request, 'attendance_history.html', data)

def profilePage(request):
    id_ = request.GET.get("u_id")
    singleuser = Gym_user.get_user_by_id(int(id_))
    user_data = {}
    user_data["a_user"] = singleuser
    height=singleuser.height
    weight=singleuser.weight
    a=weight/((height/100)**2)
    bmi=round(a,2)
    user_data['bmi']=bmi
    if bmi < 18.5 :
        category = "Underweight"
        user_data['bmi_status'] = category
    elif bmi < 25 :
        category = "Normal weight"
        user_data['bmi_status'] = category

    elif bmi < 30 :
        category = "Overweight"
        user_data['bmi_status'] = category
    else:
        category = "Obese"
        user_data['bmi_status'] = category

    return render(request, 'profile_page.html', user_data)


def searchPage(request):
    query = request.POST.get("searchedMember")
    searchedMember = Gym_user.get_searched_members(query)
    if not searchedMember:
        searchedMember = Gym_user.by_lastName(query)
        if not searchedMember:
            searchedMember = Gym_user.by_id(query)
            if not searchedMember:
                searchedMember = Gym_user.by_username(query)
                if not searchedMember:
                    searchedMember = Gym_user.by_dob(query)
    data = {}
    data["members"] = searchedMember
    return render(request, 'searchPage.html', data)