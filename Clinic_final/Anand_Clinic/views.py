import datetime
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, FormView, CreateView, UpdateView
from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.urls import reverse_lazy,reverse
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from .forms import PatientForm, MedicineForm, SimpleMedicineForm, PrescriptionGeneratorForm
from .models import FollowUp, Patient, Medicine, CheckIn, StockTransaction, Prescription, FirstDayInstruction, NextDayInstruction, User, Profile, PersonalNote
from django.conf import settings
from django.utils.dateparse import parse_datetime, parse_date
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.template.loader import render_to_string

# Anand_Clinic/views.py
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from .utils import group_required
from django.contrib.auth.views import LoginView,LogoutView
from django.shortcuts import render, redirect   
from django.urls import reverse_lazy
from django.contrib.auth.forms import AuthenticationForm

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from urllib.parse import quote
from datetime import timedelta
from .models import Profile, PasswordResetToken
from .forms import ForgotPasswordForm, ResetPasswordForm
from .models import Visit

def forgot_password(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            # Simplified flow: clinic uses a single WhatsApp number for sending reset links.
            username = form.cleaned_data['username']

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(request, "Username not found!")
                return render(request, "forgot_password.html", {"form": form})

            # create a reset token for password-only reset
            reset_token = PasswordResetToken.objects.create(user=user)
            reset_link = request.build_absolute_uri(f"/reset-password/{reset_token.token}/?mode=password")
            msg = f"Reset your password using this link: {reset_link}"

            country = getattr(settings, 'CLINIC_WHATSAPP_COUNTRY_CODE', '')
            # Use number from form if provided, else fallback to settings
            user_number = form.cleaned_data.get('whatsapp')
            if user_number:
                number = user_number.strip()
            else:
                number = getattr(settings, 'CLINIC_WHATSAPP_NUMBER', '')
                
            whatsapp_url = f"https://wa.me/{country}{number}?text={quote(msg)}"

            return render(request, "forgot_password.html", {
                "form": form,
                "whatsapp_url": whatsapp_url,
                "mode_password": True
            })

    else:
        # Do not prefill WhatsApp number; user should enter their registered number.
        form = ForgotPasswordForm()

    return render(request, "forgot_password.html", {"form": form})


def reset_password(request, token):
    token_obj = get_object_or_404(PasswordResetToken, token=token, is_used=False)
    mode = request.GET.get('mode', 'full')  # 'password' or 'full'

    if timezone.now() > token_obj.created_at + timedelta(hours=1):
        messages.error(request, "Link expired!")
        return redirect("forgot_password")

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_pwd = form.cleaned_data['new_password']
            confirm = form.cleaned_data['confirm_password']

            if new_pwd != confirm:
                messages.error(request, "Passwords do not match!")
            else:
                user = token_obj.user
                # Only update password; username changes are not supported here.
                user.set_password(new_pwd)
                user.save()
                token_obj.is_used = True
                token_obj.save()
                messages.success(request, "Password reset successful!")
                return redirect("login")
    else:
        form = ResetPasswordForm()

    return render(request, "reset_password.html", {"form": form, "mode": mode})

def manual_reset(request):
    if request.method == "POST":
        username = request.POST.get("username")
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # 1. Check username exists
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "Incorrect username or password. Please try again.")
            return redirect("Anand_Clinic:password_reset_manual")

        # 2. Verify current password
        user_auth = authenticate(username=username, password=current_password)
        if user_auth is None:
            messages.error(request, "Incorrect username or password. Please try again.")
            return redirect("Anand_Clinic:password_reset_manual")

        # 3. Validate new password match
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("Anand_Clinic:password_reset_manual")

        # SUCCESS — reset password
        user.set_password(new_password)
        user.save()

        logout(request)

        messages.success(request, "Password reset successful. Please login again.")
        return redirect("Anand_Clinic:login")

    return render(request, "password_reset_manual.html")

def logout_user(request):
    logout(request)
    return redirect('Anand_Clinic:login')

def home_redirect(request):
    # redirect root URL to 'home'
    return redirect('Anand_Clinic:index')

class RoleBasedLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = AuthenticationForm
    
    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            if user.groups.filter(name="Receptionist").exists():
                return redirect("/add_patient/")
            elif user.groups.filter(name="Doctor").exists():
                return redirect("/doctor/dashboard/")
        else:
            messages.error(request, "Invalid username or password")
            return redirect("Anand_Clinic:login")
        return render(request, self.template_name, {"error": "Invalid login"})

    def get_context_data(self, **kwargs):
        # Ensure form is always present in template
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.authentication_form()
        return context
    
class DoctorDashboard(LoginRequiredMixin, ListView):
    model = Patient
    # use the clinic.html home template (your HomePageView uses this)
    template_name = 'clinic.html'
    context_object_name = 'patients'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name="Doctor").exists():
            return redirect("Anand_Clinic:add_patient")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Apply server-side search filtering if search parameter provided
        queryset = Patient.objects.all().order_by("-last_visited", "-appointment_date")
        search = self.request.GET.get('search', '').strip()
        if search:
            from django.db.models import Q
            q = Q(case__icontains=search) | Q(name__icontains=search)
            if search.isdigit():
                q |= Q(case_no=int(search))
            if len(search) >= 3:
                q |= Q(phone_no__icontains=search)
            queryset = queryset.filter(q)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add follow-ups and today's check-ins (same as HomePageView)
        context['followups'] = FollowUp.objects.select_related('patient').filter(
            status=FollowUp.STATUS_SCHEDULED
        ).order_by('scheduled_date')[:10]
        today = timezone.now().date()
        context['today_checkins'] = CheckIn.objects.select_related('followup__patient').filter(
            checkin_time__date=today
        ).order_by('-checkin_time')[:20]
        # Add scheduled follow-ups count to each patient (used by the UI to show count)
        patients = context.get('patients', [])
        for patient in patients:
            patient.scheduled_followups_count = patient.followups.filter(status=FollowUp.STATUS_SCHEDULED).count()
        return context
    
# Create your views here.

class HomePageView(LoginRequiredMixin,TemplateView):
    login_url = '/accounts/login/'
    template_name = 'clinic.html'   #this will tell django look for a template name home.html

    model = Patient
    
    def get_context_data(self, **kwargs):    
        context =  super().get_context_data(**kwargs)
        # newest patients first
        patients = Patient.objects.prefetch_related('followups').all().order_by('-last_visited', '-appointment_date')
        # Add scheduled follow-ups count to each patient (used by the UI to show count)
        for patient in patients:
            patient.scheduled_followups_count = patient.followups.filter(status=FollowUp.STATUS_SCHEDULED).count()
        context ['patients'] = patients
        # Add all follow-ups to context
        context['followups'] = FollowUp.objects.select_related('patient').filter(
            status=FollowUp.STATUS_SCHEDULED
        ).order_by('scheduled_date')[:10]
        # Add today's check-ins
        today = timezone.now().date()
        context['today_checkins'] = CheckIn.objects.select_related('followup__patient').filter(
            checkin_time__date=today
        ).order_by('-checkin_time')[:20]
        return context 

class AddPatient(FormView):
    model = Patient
    form_class = PatientForm
    template_name = 'add_new_patient.html'
    success_url = reverse_lazy('Anand_Clinic:patient_list') 

    def form_valid(self, form):
        data = form.cleaned_data
        phone = data.get('phone_no')
        case = data.get('case')
        name = data.get('name')
        now = timezone.now()

        existing = Patient.objects.filter(case=case).first()

        if existing:
            existing.last_visited = now
            existing.save(update_fields=['last_visited'])
            Visit.objects.create(patient=existing, visit_datetime=now)
            messages.success(self.request, f'Updated visit for existing patient "{existing.name}".')
            return redirect('Anand_Clinic:patient_list')

        self.object = form.save(commit=False)
        self.object.last_visited = now
        self.object.save()
        Visit.objects.create(patient=self.object, visit_datetime=now)
        messages.success(self.request, f'Patient "{self.object.name}" added successfully!')
        return redirect('Anand_Clinic:patient_list')

class PatientsView(ListView):
    template_name = 'patient_list.html'
    model = Patient

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Patient.objects.prefetch_related('followups').all().order_by('-last_visited', '-appointment_date')
        search = self.request.GET.get('search', '')
        if search:
            s = search.strip()
            # Start with name and case matches (always useful)
            q = Q(case__icontains=s) | Q(name__icontains=s)
            # If it's numeric, consider exact case_no match and allow phone substring
            # only for reasonably long digit queries (avoid matching single digits present in most phone numbers).
            if s.isdigit():
                try:
                    q |= Q(case_no=int(s))
                except ValueError:
                    pass
                if len(s) >= 3:
                    q |= Q(phone_no__icontains=s)
            else:
                # For textual queries, also allow phone substring matches
                q |= Q(phone_no__icontains=s)

            qs = qs.filter(q)

        unique = []
        seen = set()
        for patient in qs:
            key = getattr(patient, 'case_no', None) or getattr(patient, 'phone_no', None) or patient.name
            if key in seen:
                continue
            seen.add(key)
            patient.scheduled_followups_count = patient.followups.filter(status=FollowUp.STATUS_SCHEDULED).count()
            unique.append(patient)
        context['patients'] = unique
        # When rendering the dedicated patient list page, hide the base toolbar/list UI that
        # is used by the home page to avoid duplicate/conflicting search inputs and JS.
        context['hide_toolbar'] = True
        return context
    
class PatientDetailView(DetailView):
    template_name = 'detail.html'
    model = Patient
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        
        visits = patient.visits.all()
        # order visits ascending for summary (oldest first) and for grouping
        visits_asc = visits.order_by('visit_datetime')
        followups = patient.followups.select_related('patient').prefetch_related('checkins').order_by('scheduled_date')
        checkins = CheckIn.objects.filter(followup__patient=patient).select_related('followup__patient').order_by('checkin_time')
        prescriptions = patient.generated_prescriptions.prefetch_related('first_day_instructions', 'next_day_instructions', 'visit').order_by('-created_at')

        timeline = []
        if patient.appointment_date:
            timeline.append({
                'type': 'appointment',
                'date': patient.appointment_date,
                'title': 'Initial Appointment',
                'data': patient
            })

        for visit in visits:
            timeline.append({
                'type': 'visit',
                'date': visit.visit_datetime,
                'title': 'Visit',
                'data': visit,
            })

        for checkin in checkins:
            timeline.append({
                'type': 'checkin',
                'date': checkin.checkin_time,
                'title': f'Check-in - {checkin.get_status_display()}',
                'data': checkin,
                'parent_followup': checkin.followup
            })

        for prescription in prescriptions:
            timeline.append({
                'type': 'prescription',
                'date': prescription.created_at,
                'title': 'Prescription Issued',
                'data': prescription
            })

        timeline.sort(key=lambda x: x['date'])

        # Compute visit summary: first/last dates and total visits (count visits; include registration as a visit if none exist)
        if visits_asc.exists():
            first_visit_date = visits_asc.first().visit_datetime
            last_visit_date = visits_asc.last().visit_datetime
            total_visits = visits_asc.count()
        else:
            # No Visit objects — treat appointment_date as the single registration visit if present
            first_visit_date = patient.appointment_date
            last_visit_date = patient.appointment_date
            total_visits = 1 if patient.appointment_date else 0
        
        # Determine back URL based on user role
        user = self.request.user
        if user.groups.filter(name="Receptionist").exists():
            context['back_url'] = 'Anand_Clinic:patient_list'
            context['back_text'] = 'Back to Patient List'
        elif user.groups.filter(name="Doctor").exists():
            context['back_url'] = 'Anand_Clinic:doctor_dashboard'
            context['back_text'] = 'Back to Home'
        else:
            context['back_url'] = 'Anand_Clinic:index'
            context['back_text'] = 'Back to Home'
        
        context['followups'] = followups
        context['checkins'] = checkins
        context['prescriptions'] = prescriptions
        context['visits'] = visits_asc
        context['first_visit_date'] = first_visit_date
        context['last_visit_date'] = last_visit_date
        context['total_visits'] = total_visits
        # When rendering patient detail page we prefer to hide the side cards (follow-ups/check-ins)
        context['hide_side_cards'] = True
        context['timeline'] = timeline
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user
        if not user.groups.filter(name="Doctor").exists():
            return redirect("Anand_Clinic:patient_details", pk=self.object.pk)
        case_val = request.POST.get("case", "").strip()
        phone_val = request.POST.get("phone_no", "").strip()
        fields_to_update = []
        if case_val and case_val != (self.object.case or ""):
            self.object.case = case_val
            fields_to_update.append("case")
        if phone_val and phone_val != (self.object.phone_no or ""):
            self.object.phone_no = phone_val
            fields_to_update.append("phone_no")
        if fields_to_update:
            self.object.save(update_fields=fields_to_update)
        return redirect("Anand_Clinic:patient_details", pk=self.object.pk)

@login_required
def personal_note_get(request, pk):
    """Return the logged-in doctor's personal note for the given patient."""
    # Only doctors can access personal notes
    if not request.user.groups.filter(name="Doctor").exists():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        patient = Patient.objects.get(pk=pk)
    except Patient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Patient not found'}, status=404)
    note = PersonalNote.objects.filter(doctor=request.user, patient=patient).first()
    image_urls = []
    if note:
        if note.image:
            try:
                image_urls.append(note.image.url)
            except:
                pass
        try:
            image_urls.extend([img.image.url for img in note.images.all().order_by('created_at') if img.image])
        except:
            pass
    image_url = image_urls[0] if image_urls else None
    return JsonResponse({
        'success': True,
        'note': note.note if note else '',
        'image_url': image_url,
        'image_urls': image_urls
    })

@login_required
@require_POST
def personal_note_save(request, pk):
    """Create a new personal note for the patient."""
    if not request.user.groups.filter(name="Doctor").exists():
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        patient = Patient.objects.get(pk=pk)
    except Patient.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Patient not found'}, status=404)
    note_text = request.POST.get('note', '').strip()
    
    # Only create note if there's text or images
    files = request.FILES.getlist('image')
    if not files and 'image' in request.FILES:
        files = [request.FILES['image']]
    
    if not note_text and not files:
        return JsonResponse({'success': False, 'error': 'Note text or image is required'}, status=400)
    
    # Create new note
    obj = PersonalNote.objects.create(doctor=request.user, patient=patient, note=note_text)
    
    # Add images
    for f in files:
        try:
            from .models import PersonalNoteImage
            PersonalNoteImage.objects.create(note=obj, image=f)
        except Exception as e:
            # If creating related image fails, still save note text
            pass
    
    return JsonResponse({'success': True, 'message': 'Personal note saved successfully.', 'note_id': obj.id})

@login_required
def personal_notes_list(request, pk):
    """View all personal notes for a patient."""
    if not request.user.groups.filter(name="Doctor").exists():
        return redirect('Anand_Clinic:patient_details', pk=pk)
    try:
        patient = Patient.objects.get(pk=pk)
    except Patient.DoesNotExist:
        messages.error(request, 'Patient not found')
        return redirect('Anand_Clinic:index')
    
    # Get all notes for this patient by the current doctor
    notes = PersonalNote.objects.filter(doctor=request.user, patient=patient).order_by('-created_at')
    
    # Get images for each note
    notes_with_images = []
    for note in notes:
        image_urls = []
        if note.image:
            try:
                image_urls.append(note.image.url)
            except:
                pass
        try:
            image_urls.extend([img.image.url for img in note.images.all().order_by('created_at') if img.image])
        except:
            pass
        notes_with_images.append({
            'note': note,
            'image_urls': image_urls
        })
    
    context = {
        'patient': patient,
        'notes_with_images': notes_with_images
    }
    return render(request, 'personal_notes_list.html', context)

class FollowUpsView(TemplateView):
    template_name = 'follow_ups.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['followups'] = FollowUp.objects.select_related('patient').order_by('-scheduled_date')
        return context

class CheckInsView(ListView):
    model = CheckIn
    template_name = 'checkin_list.html'
    context_object_name = 'checkins'
    paginate_by = 50
    
    def get_doctor_code_for_user(self, user):
        """Determine doctor code based on logged-in user.
        Returns 'dr_1', 'dr_2', or None if not a doctor or cannot determine.
        """
        if not user.is_authenticated:
            return None
        if not user.groups.filter(name="Doctor").exists():
            return None
        # Check username for doctor identification
        username_lower = user.username.lower()
        if 'ami' in username_lower or 'dr1' in username_lower or username_lower.startswith('dr_1'):
            return 'dr_1'
        elif 'kaushal' in username_lower or 'dr2' in username_lower or username_lower.startswith('dr_2'):
            return 'dr_2'
        return None
    
    def get_queryset(self):
        queryset = CheckIn.objects.select_related('followup__patient').order_by('-checkin_time')
        
        # Filter by logged-in doctor if user is a doctor
        doctor_code = self.get_doctor_code_for_user(self.request.user)
        if doctor_code:
            queryset = queryset.filter(
                Q(followup__patient__doctor=doctor_code) |
                Q(followup__patient__doctor='Dr Ami Bhatt' if doctor_code == 'dr_1' else 'Dr Kaushal Bhatt')
            )
        
        search_query = self.request.GET.get('search', '')
        status = self.request.GET.get('status', '')
        date_filter = self.request.GET.get('date', '')
        # Single scheduled and checkin filters (date or datetime)
        scheduled = self.request.GET.get('scheduled', '')
        checkin = self.request.GET.get('checkin', '')
        doctor = self.request.GET.get('doctor', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(followup__patient__name__icontains=search_query) |
                Q(followup__patient__case_no__icontains=search_query)
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        if date_filter:
            queryset = queryset.filter(checkin_time__date=date_filter)

        # Parse a single date/datetime string and return a date object
        def _parse_to_date(val):
            if not val:
                return None
            dt = parse_datetime(val)
            if dt:
                return dt.date()
            d = parse_date(val)
            if d:
                return d
            return None

        s_date = _parse_to_date(scheduled)
        if s_date:
            queryset = queryset.filter(followup__scheduled_date__date=s_date)

        c_date = _parse_to_date(checkin)
        if c_date:
            queryset = queryset.filter(checkin_time__date=c_date)
        
        if doctor:
            # Handle both old format (full name) and new format (code)
            if doctor == 'dr_1':
                queryset = queryset.filter(
                    Q(followup__patient__doctor='dr_1') |
                    Q(followup__patient__doctor='Dr Ami Bhatt')
                )
            elif doctor == 'dr_2':
                queryset = queryset.filter(
                    Q(followup__patient__doctor='dr_2') |
                    Q(followup__patient__doctor='Dr Kaushal Bhatt')
                )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_checkins'] = CheckIn.objects.count()
        context['early_count'] = CheckIn.objects.filter(status=CheckIn.STATUS_EARLY).count()
        context['on_time_count'] = CheckIn.objects.filter(status=CheckIn.STATUS_ON_TIME).count()
        context['late_count'] = CheckIn.objects.filter(status=CheckIn.STATUS_LATE).count()
        context['doctor_choices'] = [('dr_1', 'Dr. Ami Bhatt'), ('dr_2', 'Dr. Kaushal Bhatt')]
        # Count check-ins by doctor - handle both old format (full name) and new format (code)
        context['ami_count'] = CheckIn.objects.filter(
            Q(followup__patient__doctor='dr_1') |
            Q(followup__patient__doctor='Dr Ami Bhatt')
        ).count()
        context['kaushal_count'] = CheckIn.objects.filter(
            Q(followup__patient__doctor='dr_2') |
            Q(followup__patient__doctor='Dr Kaushal Bhatt')
        ).count()
        return context

class PharmacyView(TemplateView):
    template_name = 'pharmacy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['medicines'] = Medicine.objects.all()[:10]
        context['low_stock_medicines'] = Medicine.objects.filter(
            stock_quantity__lte=F('reorder_level')
        )[:5]
        context['total_medicines'] = Medicine.objects.count()
        context['total_patients'] = Patient.objects.count()
        # Add all patients and medicines for inline forms
        context['all_patients'] = Patient.objects.all().order_by('name')
        context['all_medicines'] = Medicine.objects.all().order_by('name')
        return context


# Medicine Views
class MedicineListView(ListView):
    model = Medicine
    template_name = 'medicine_list.html'
    context_object_name = 'medicines'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Medicine.objects.all()
        search_query = self.request.GET.get('search', '')
        medicine_type = self.request.GET.get('type', '')
        low_stock = self.request.GET.get('low_stock', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(generic_name__icontains=search_query) |
                Q(manufacturer__icontains=search_query)
            )
        
        if medicine_type:
            queryset = queryset.filter(medicine_type=medicine_type)
        
        if low_stock == 'true':
            queryset = queryset.filter(stock_quantity__lte=F('reorder_level'))
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['low_stock_count'] = Medicine.objects.filter(
            stock_quantity__lte=F('reorder_level')
        ).count()
        context['expired_count'] = Medicine.objects.filter(
            expiry_date__lt=timezone.now().date()
        ).count()
        return context


class MedicineCreateView(CreateView):
    model = Medicine
    # Use simplified form for quick add (only name and quantity)
    form_class = SimpleMedicineForm
    template_name = 'medicine_form.html'
    success_url = reverse_lazy('Anand_Clinic:medicine_list')
    
    def form_valid(self, form):
        # Save object first
        self.object = form.save()
        messages.success(self.request, f'Medicine "{form.cleaned_data["name"]}" added successfully!')
        # Handle AJAX requests: return JSON with created object summary
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'id': self.object.pk,
                'name': self.object.name,
                'stock_quantity': self.object.stock_quantity,
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        # Return JSON errors for AJAX
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        return super().form_invalid(form)


@require_POST
def dispense_medicine_ajax(request, pk):
    """AJAX endpoint to reduce medicine stock.

    Expects POST: quantity (int), optional reason
    Returns JSON: { success: True, new_stock: int }
    """
    try:
        med = Medicine.objects.get(pk=pk)
    except Medicine.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Medicine not found.'}, status=404)

    qty = request.POST.get('quantity')
    reason = request.POST.get('reason', 'dispensed')

    try:
        qty = int(qty)
        if qty <= 0:
            raise ValueError()
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid quantity.'}, status=400)

    # reduce stock (never negative)
    removed = min(qty, med.stock_quantity)
    med.stock_quantity = med.stock_quantity - removed
    med.save(update_fields=['stock_quantity'])

    # Record stock transaction
    StockTransaction.objects.create(
        medicine=med,
        change=-removed,
        reason=reason
    )

    return JsonResponse({'success': True, 'new_stock': med.stock_quantity, 'removed': removed})


@require_POST
def update_stock_ajax(request, pk):
    """AJAX endpoint to add or set medicine stock.

    Expects POST: quantity (int), mode ('add' or 'set'), optional reason
    Returns JSON: { success: True, new_stock: int, delta: int }
    """
    try:
        med = Medicine.objects.get(pk=pk)
    except Medicine.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Medicine not found.'}, status=404)

    qty = request.POST.get('quantity')
    mode = request.POST.get('mode', 'add')
    reason = request.POST.get('reason', 'stock_update')

    try:
        qty = int(qty)
        if qty < 0:
            raise ValueError()
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid quantity.'}, status=400)

    if mode == 'add':
        delta = qty
        med.stock_quantity = med.stock_quantity + delta
        med.save(update_fields=['stock_quantity'])
        StockTransaction.objects.create(medicine=med, change=delta, reason=reason)
        return JsonResponse({'success': True, 'new_stock': med.stock_quantity, 'delta': delta})
    elif mode == 'set':
        old = med.stock_quantity
        med.stock_quantity = qty
        med.save(update_fields=['stock_quantity'])
        delta = med.stock_quantity - old
        StockTransaction.objects.create(medicine=med, change=delta, reason=reason)
        return JsonResponse({'success': True, 'new_stock': med.stock_quantity, 'delta': delta})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid mode.'}, status=400)


class MedicineUpdateView(UpdateView):
    model = Medicine
    form_class = MedicineForm
    template_name = 'medicine_form.html'
    success_url = reverse_lazy('Anand_Clinic:medicine_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Medicine "{form.instance.name}" updated successfully!')
        response = super().form_valid(form)
        # Handle AJAX requests
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponse(status=200)
        return response


class MedicineDetailView(DetailView):
    model = Medicine
    template_name = 'medicine_detail.html'
    context_object_name = 'medicine'



# my code for follow-up...

@require_POST
def create_followup_ajax(request):
    """
    Expects: patient_id, scheduled_date (from input type=datetime-local -> "YYYY-MM-DDTHH:MM")
    Returns JSON: { success: true, followup: {...} } or { success: false, error: "..." }
    This version does NOT require login. created_by will be set only if request.user.is_authenticated.
    """
    patient_id = request.POST.get('patient_id')
    scheduled_date_str = request.POST.get('scheduled_date')

    if not patient_id or not scheduled_date_str:
        return JsonResponse({'success': False, 'error': 'Missing patient or date.'}, status=400)

    try:
        patient = Patient.objects.get(pk=int(patient_id))
    except (Patient.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Patient not found.'}, status=404)

    # parse datetime-local string. It typically has no timezone info.
    try:
        if len(scheduled_date_str.split(':')) == 2:
            scheduled_date_str = scheduled_date_str + ':00'
        dt = parse_datetime(scheduled_date_str)
        if dt is None:
            dt = datetime.fromisoformat(scheduled_date_str)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid date format.'}, status=400)

    # Make timezone-aware if naive
    if timezone.is_naive(dt):
        current_tz = timezone.get_current_timezone()
        dt = timezone.make_aware(dt, current_tz)

    # Validate date not in past
    if dt < timezone.now():
        return JsonResponse({'success': False, 'error': 'Cannot schedule a follow-up in the past.'}, status=400)

    # Allow multiple scheduled follow-ups for the same patient.
    # Previous logic prevented creating more than one scheduled follow-up per patient;
    # removing that restriction so receptionists/doctors can schedule multiple future follow-ups.

    # Create follow-up; set created_by only if authenticated
    try:
        created_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        fu = FollowUp.objects.create(
            patient=patient,
            scheduled_date=dt,
            created_by=created_by,
            status=FollowUp.STATUS_SCHEDULED
        )
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    local_scheduled = timezone.localtime(fu.scheduled_date)
    scheduled_attr = local_scheduled.strftime('%Y-%m-%d %H:%M')
    scheduled_display = local_scheduled.strftime('%b %d, %Y %H:%M')

    return JsonResponse({
        'success': True,
        'followup': {
            'id': fu.pk,
            'patient_id': patient.pk,
            'patient_name': getattr(patient, 'name', str(patient)),
            'doctor_display': patient.get_doctor_display(),
            'scheduled_date': fu.scheduled_date.isoformat(),
            'scheduled_date_attr': scheduled_attr,
            'scheduled_date_display': scheduled_display,
            'status': fu.status,
        }
    })


@require_POST
def create_checkin_ajax(request):
    """AJAX endpoint to record a check-in for a follow-up.
    Expects: followup_id
    Returns JSON with checkin status: early/on_time/late and minutes difference.
    """
    followup_id = request.POST.get('followup_id')
    if not followup_id:
        return JsonResponse({'success': False, 'error': 'Missing followup id.'}, status=400)

    try:
        fu = FollowUp.objects.select_related('patient').get(pk=int(followup_id))
    except (FollowUp.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Follow-up not found.'}, status=404)

    now = timezone.now()
    scheduled = fu.scheduled_date
    # Ensure both are timezone-aware
    if timezone.is_naive(scheduled):
        scheduled = timezone.make_aware(scheduled, timezone.get_current_timezone())

    diff = (now - scheduled).total_seconds()
    minutes = int(diff // 60)

    if diff < 0:
        status = CheckIn.STATUS_EARLY
    elif diff > 3 * 3600:
        status = CheckIn.STATUS_LATE
    else:
        status = CheckIn.STATUS_ON_TIME

    created_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

    checkin = CheckIn.objects.create(
        followup=fu,
        checkin_time=now,
        status=status,
        minutes_difference=minutes,
        created_by=created_by
    )

    local_checkin = timezone.localtime(checkin.checkin_time)
    checkin_time_attr = local_checkin.strftime('%Y-%m-%d %H:%M')
    checkin_time_display = local_checkin.strftime('%b %d, %Y %H:%M')

    # Mark follow-up as completed on check-in
    # Save check-in fields on the follow-up for direct reference
    fu.checkin_time = now
    fu.checkin_status = status
    fu.checkin_minutes_difference = minutes
    fu.checkin_by = created_by
    fu.status = FollowUp.STATUS_COMPLETED
    fu.save(update_fields=['checkin_time', 'checkin_status', 'checkin_minutes_difference', 'checkin_by', 'status'])

    return JsonResponse({
        'success': True,
        'checkin': {
            'id': checkin.pk,
            'followup_id': fu.pk,
            'patient_id': fu.patient.pk,
            'patient_name': fu.patient.name,
            'doctor_display': fu.patient.get_doctor_display(),
            'checkin_time': checkin.checkin_time.isoformat(),
            'checkin_time_attr': checkin_time_attr,
            'checkin_time_display': checkin_time_display,
            'status': checkin.status,
            'minutes_difference': checkin.minutes_difference,
        }
    })

# Prescription section.

class PrescriptionGeneratorCreateView(TemplateView):
    template_name = 'prescription_generator_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PrescriptionGeneratorForm()
        context['patients'] = Patient.objects.all().order_by('name')
        return context

    def post(self, request, *args, **kwargs):
        form = PrescriptionGeneratorForm(request.POST)
        if form.is_valid():
            patient = form.cleaned_data['patient']
            case_input = form.cleaned_data.get('case_number', '')
            
            p_case = case_input
            p_case_number = 0
            if case_input and str(case_input).isdigit():
                p_case_number = int(case_input)

            latest_visit = Visit.objects.filter(patient=patient).order_by('-visit_datetime').first()
            prescription = Prescription.objects.create(
                patient=patient,
                visit=latest_visit,
                case=p_case,
                case_number=p_case_number,
                prescribed_by_ami=bool(request.POST.get('doctor_ami')),
                prescribed_by_kaushal=bool(request.POST.get('doctor_kaushal')),
                language=request.POST.get('language', 'en')
            )

            first_total = int(request.POST.get('first_TOTAL', '0') or '0')
            for i in range(first_total):
                size = request.POST.get(f'first-{i}-size')
                label = request.POST.get(f'first-{i}-label')
                pills = request.POST.get(f'first-{i}-pills')
                unit = request.POST.get(f'first-{i}-unit', 'pill')
                
                time_list = []
                if request.POST.get(f'first-{i}-time_morning'): time_list.append('Morning')
                if request.POST.get(f'first-{i}-time_afternoon'): time_list.append('Afternoon')
                if request.POST.get(f'first-{i}-time_evening'): time_list.append('Evening')
                if request.POST.get(f'first-{i}-time_night'): time_list.append('Night')
                time = ", ".join(time_list)

                special = request.POST.get(f'first-{i}-special', '')
                if size and label and pills and time:
                    qty = pills or ''
                    if prescription.language == 'gu':
                        unit_word = 'ગોળીઓ' if unit == 'pill' else 'ટીપાં'
                    else:
                        unit_word = 'pills' if unit == 'pill' else 'drops'
                    qty_text = f"{qty} {unit_word}".strip()
                    FirstDayInstruction.objects.create(
                        prescription=prescription,
                        size_of_bottle=size,
                        label=label,
                        no_of_pill=qty_text,
                        time_of_day=time,
                        special_instruction=special,
                    )

            next_total = int(request.POST.get('next_TOTAL', '0') or '0')
            for i in range(next_total):
                bottle_no = request.POST.get(f'next-{i}-bottle')
                pills = request.POST.get(f'next-{i}-pills')
                unit = request.POST.get(f'next-{i}-unit', 'pill')
                
                time_list = []
                if request.POST.get(f'next-{i}-time_morning'): time_list.append('Morning')
                if request.POST.get(f'next-{i}-time_afternoon'): time_list.append('Afternoon')
                if request.POST.get(f'next-{i}-time_evening'): time_list.append('Evening')
                if request.POST.get(f'next-{i}-time_night'): time_list.append('Night')
                time = ", ".join(time_list)

                special = request.POST.get(f'next-{i}-special', '')
                if bottle_no and pills and time:
                    qty = pills or ''
                    if prescription.language == 'gu':
                        unit_word = 'ગોળી' if unit == 'pill' else 'ટીપાં'
                    else:
                        unit_word = 'pills' if unit == 'pill' else 'drops'
                    qty_text = f"{qty} {unit_word}".strip()
                    NextDayInstruction.objects.create(
                        prescription=prescription,
                        bottle_no=bottle_no,
                        no_of_pill=qty_text,
                        dose='', # dose is removed from UI
                        time_of_day=time,
                        special_instruction=special,
                    )

            # After all instructions are added, calculate and save the printed height
            prescription.printed_height_mm = prescription.calculate_printed_height_mm()
            
            # Calculate top margin for this prescription based on patient's page state
            # A4 page dimensions with margins
            A4_HEIGHT_MM = 297
            MARGIN_MM = 20  # top and bottom margins
            MARGIN_GAP_MM = 10
            
            # Determine the absolute lower position of the last prescription for this patient.
            # This avoids relying on a possibly stale `patient.page_lower_margin_mm` value.
            prev_prescription = Prescription.objects.filter(
                patient=patient
            ).exclude(pk=prescription.pk).order_by('-created_at').first()

            if prev_prescription:
                prev_abs_top = MARGIN_MM + prev_prescription.top_margin_mm
                # Recalculate previous prescription's height to ensure it's current
                prev_height = prev_prescription.calculate_printed_height_mm()
                prev_lower_abs = prev_abs_top + prev_height
            else:
                prev_lower_abs = MARGIN_MM  # page top

            # Proposed absolute top is previous lower + gap
            proposed_top_margin_abs = prev_lower_abs + MARGIN_GAP_MM
            proposed_bottom_abs = proposed_top_margin_abs + prescription.printed_height_mm

            # If it doesn't fit in the current page's full height, move to next page.
            if proposed_bottom_abs > A4_HEIGHT_MM:
                # Move to new page. Store top_margin relative to printable area (gap only)
                prescription.top_margin_mm = MARGIN_GAP_MM  # 10mm (relative)
                # Update patient's absolute lower margin: page top margin + relative top + height
                patient.page_lower_margin_mm = MARGIN_MM + prescription.top_margin_mm + prescription.printed_height_mm
            else:
                # Fits on current page: store top margin relative to printable area
                # Clamp to at least the MARGIN_GAP_MM so first-prescription doesn't become negative
                prescription.top_margin_mm = max(MARGIN_GAP_MM, proposed_top_margin_abs - MARGIN_MM)
                # Update patient's absolute lower margin based on stored relative top
                patient.page_lower_margin_mm = MARGIN_MM + prescription.top_margin_mm + prescription.printed_height_mm
            
            prescription.save(update_fields=['printed_height_mm', 'top_margin_mm'])
            patient.save(update_fields=['page_lower_margin_mm'])

            return redirect('Anand_Clinic:prescription_generator_detail', pk=prescription.pk)
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class PrescriptionGeneratorUpdateView(TemplateView):
    template_name = 'prescription_generator_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PrescriptionGeneratorForm()
        context['patients'] = Patient.objects.all().order_by('name')
        context['prescription'] = Prescription.objects.get(pk=self.kwargs['pk'])
        return context

    def post(self, request, *args, **kwargs):
        prescription = Prescription.objects.get(pk=self.kwargs['pk'])
        form = PrescriptionGeneratorForm(request.POST)
        if form.is_valid():
            prescription.patient = form.cleaned_data['patient']
            prescription.visit = Visit.objects.filter(patient=prescription.patient).order_by('-visit_datetime').first()
            
            case_input = form.cleaned_data.get('case_number', '')
            prescription.case = case_input
            if case_input and str(case_input).isdigit():
                prescription.case_number = int(case_input)
            else:
                prescription.case_number = 0
                
            prescription.prescribed_by_ami = bool(request.POST.get('doctor_ami'))
            prescription.prescribed_by_kaushal = bool(request.POST.get('doctor_kaushal'))
            prescription.language = request.POST.get('language', prescription.language)
            prescription.save()

            prescription.first_day_instructions.all().delete()
            prescription.next_day_instructions.all().delete()

            first_total = int(request.POST.get('first_TOTAL', '0') or '0')
            for i in range(first_total):
                size = request.POST.get(f'first-{i}-size')
                label = request.POST.get(f'first-{i}-label')
                pills = request.POST.get(f'first-{i}-pills')
                unit = request.POST.get(f'first-{i}-unit', 'pill')
                
                time_list = []
                if request.POST.get(f'first-{i}-time_morning'): time_list.append('Morning')
                if request.POST.get(f'first-{i}-time_afternoon'): time_list.append('Afternoon')
                if request.POST.get(f'first-{i}-time_evening'): time_list.append('Evening')
                if request.POST.get(f'first-{i}-time_night'): time_list.append('Night')
                time = ", ".join(time_list)

                special = request.POST.get(f'first-{i}-special', '')
                if size and label and pills and time:
                    qty = pills or ''
                    if prescription.language == 'gu':
                        unit_word = 'ગોળીઓ' if unit == 'pill' else 'ટીપાં'
                    else:
                        unit_word = 'pills' if unit == 'pill' else 'drops'
                    qty_text = f"{qty} {unit_word}".strip()
                    FirstDayInstruction.objects.create(
                        prescription=prescription,
                        size_of_bottle=size,
                        label=label,
                        no_of_pill=qty_text,
                        time_of_day=time,
                        special_instruction=special,
                    )

            next_total = int(request.POST.get('next_TOTAL', '0') or '0')
            for i in range(next_total):
                bottle_no = request.POST.get(f'next-{i}-bottle')
                pills = request.POST.get(f'next-{i}-pills')
                unit = request.POST.get(f'next-{i}-unit', 'pill')
                
                time_list = []
                if request.POST.get(f'next-{i}-time_morning'): time_list.append('Morning')
                if request.POST.get(f'next-{i}-time_afternoon'): time_list.append('Afternoon')
                if request.POST.get(f'next-{i}-time_evening'): time_list.append('Evening')
                if request.POST.get(f'next-{i}-time_night'): time_list.append('Night')
                time = ", ".join(time_list)

                special = request.POST.get(f'next-{i}-special', '')
                if bottle_no and pills and time:
                    qty = pills or ''
                    if prescription.language == 'gu':
                        unit_word = 'ગોળી' if unit == 'pill' else 'ટીપાં'
                    else:
                        unit_word = 'pills' if unit == 'pill' else 'drops'
                    qty_text = f"{qty} {unit_word}".strip()
                    NextDayInstruction.objects.create(
                        prescription=prescription,
                        bottle_no=bottle_no,
                        no_of_pill=qty_text,
                        dose='',
                        time_of_day=time,
                        special_instruction=special,
                    )

            # After all instructions are updated, recalculate and save the printed height
            # Note: We DON'T recalculate top_margin_mm here because it was set at creation
            # and should not change even if the prescription is edited
            prescription.printed_height_mm = prescription.calculate_printed_height_mm()
            prescription.save(update_fields=['printed_height_mm'])

            return redirect('Anand_Clinic:prescription_generator_detail', pk=prescription.pk)
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class PrescriptionGeneratorDetailView(TemplateView):
    template_name = 'prescription_generator_print.html'

    def dispatch(self, request, *args, **kwargs):
        # Only doctors may view/print prescription PDFs
        if not request.user.is_authenticated or not request.user.groups.filter(name="Doctor").exists():
            return redirect('Anand_Clinic:patient_list')
        return super().dispatch(request, *args, **kwargs)

    def format_prescription(self, p):
        """Format a prescription to text. Returns list of lines."""
        lines = []
        if p.language == 'gu':
            size_map = {'Small': 'નાની', 'Medium': 'મધ્યમ', 'Large': 'મોટી'}
            dose_map = {'one': 'એક', 'two': 'બે', 'three': 'ત્રણ', 'four': 'ચાર', 'five': 'પાંચ'}
            time_map = {'Afternoon': 'બપોરે', 'Morning': 'સવારે', 'Night': 'રાતના', 'Evening': 'સાંજે'}
            lines.append('To,')
            lines.append(f"{p.patient.name} (કેસ નંબર. {p.case if p.case else p.case_number}),")
            lines.append('દવા લેવાની રીત')
            lines.append('')
            lines.append('પહેલા દિવસે:')
            for fd in p.first_day_instructions.all():
                size = size_map.get(fd.size_of_bottle, fd.size_of_bottle)
                
                # Handle multiple times
                raw_times = fd.time_of_day.split(',')
                mapped_times = [time_map.get(t.strip(), t.strip()) for t in raw_times if t.strip()]
                time = ", ".join(mapped_times)
                
                base = f"☑ {size} બોટલ: '{fd.label}' તરીકે લેબલ થયેલ: {time} સમયે {fd.no_of_pill} લો."
                if fd.special_instruction:
                    base = f"☑ {size} બોટલ: '{fd.label}' તરીકે લેબલ થયેલ: {time} સમયે {fd.no_of_pill} લો {fd.special_instruction}"
                lines.append(base)
            lines.append('')
            lines.append("એના પછીના બીજા દિવસ થી:")
            for nd in p.next_day_instructions.all():
                raw_times = nd.time_of_day.split(',')
                mapped_times = [time_map.get(t.strip(), t.strip()) for t in raw_times if t.strip()]
                time = ", ".join(mapped_times)
                line = f"☑ બોટલ નંબર. {nd.bottle_no} માંથી: {nd.no_of_pill}, {time} સમયે."
                if nd.special_instruction:
                    line = f"☑ બોટલ નંબર. {nd.bottle_no} માંથી: {nd.no_of_pill}, {time} સમયે {nd.special_instruction}"
                lines.append(line)
        else:
            lines.append('To,')
            lines.append(f"{p.patient.name} (Case No. {p.case if p.case else p.case_number}),")
            lines.append('You have to take Homeopathic Medicine in the following order:')
            lines.append('')
            lines.append('On First Day:')
            for fd in p.first_day_instructions.all():
                base = f"☑ {fd.size_of_bottle} Bottle: Labeled as '{fd.label}': take {fd.no_of_pill} at {fd.time_of_day}."
                if fd.special_instruction:
                    base = f"☑ {fd.size_of_bottle} Bottle: Labeled as '{fd.label}': take {fd.no_of_pill} at {fd.time_of_day} {fd.special_instruction}"
                lines.append(base)
            lines.append('')
            lines.append('From Next day onwards:')
            for nd in p.next_day_instructions.all():
                line = f"☑ From Bottle No. {nd.bottle_no}: {nd.no_of_pill} at {nd.time_of_day}."
                if nd.special_instruction:
                    line = f"☑ From Bottle No. {nd.bottle_no}: {nd.no_of_pill} at {nd.time_of_day} {nd.special_instruction}"
                lines.append(line)
        
        lines.append('')
        doctor_names = []
        if p.prescribed_by_ami:
            doctor_names.append('Dr. Ami Bhatt')
        if p.prescribed_by_kaushal:
            doctor_names.append('Dr. Kaushal Bhatt')
        if len(doctor_names) == 2:
            lines.append('Dr. Ami Bhatt                Dr. Kaushal Bhatt')
        elif len(doctor_names) == 1:
            lines.append(doctor_names[0])
        else:
            lines.append('Dr. Ami Bhatt                Dr. Kaushal Bhatt')
        
        return lines

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        p = Prescription.objects.get(pk=self.kwargs['pk'])
        lines = []
        if p.language == 'gu':
            size_map = {'Small': 'નાની', 'Medium': 'મધ્યમ', 'Large': 'મોટી'}
            dose_map = {'one': 'એક', 'two': 'બે', 'three': 'ત્રણ', 'four': 'ચાર', 'five': 'પાંચ'}
            time_map = {'Day': 'દિવસ', 'Morning': 'સવારે', 'Night': 'રાત્રે'}
            lines.append('દવા લેવાની રીત')
            lines.append('To,')
            lines.append(f"{p.patient.name} (કેસ નંબર. {p.case if p.case else p.case_number}),")
            lines.append('તમારે નીચે મુજબ હોમિયોપેથીની દવા લેવી છે:')
            lines.append('')
            lines.append('પહેલા દિવસે:')
            for fd in p.first_day_instructions.all():
                size = size_map.get(fd.size_of_bottle, fd.size_of_bottle)
                
                # Handle multiple times
                raw_times = fd.time_of_day.split(',')
                mapped_times = [time_map.get(t.strip(), t.strip()) for t in raw_times if t.strip()]
                time = ", ".join(mapped_times)
                
                base = f"☑ {size} બોટલ: ‘{fd.label}’ તરીકે લેબલ થયેલ: {time} સમયે {fd.no_of_pill} ગોળીઓ લો."
                if fd.special_instruction:
                    base = f"☑ {size} બોટલ: ‘{fd.label}’ તરીકે લેબલ થયેલ: {time} સમયે {fd.no_of_pill} ગોળીઓ લો {fd.special_instruction}"
                lines.append(base)
            lines.append('')
            lines.append('એના પછીના બીજા દિવસથી,:')
            for nd in p.next_day_instructions.all():
                raw_times = nd.time_of_day.split(',')
                mapped_times = [time_map.get(t.strip(), t.strip()) for t in raw_times if t.strip()]
                time = ", ".join(mapped_times)
                line = f"☑ બોટલ નંબર. {nd.bottle_no} માંથી: {nd.no_of_pill} ગોળી, {time} સમયે."
                if nd.special_instruction:
                    line = f"☑ બોટલ નંબર. {nd.bottle_no} માંથી: {nd.no_of_pill} ગોળી, {time} સમયે {nd.special_instruction}"
                lines.append(line)
        else:
            lines.append('Instructions for Medicinal Distribution')
            lines.append('To,')
            lines.append(f"{p.patient.name} (Case No. {p.case if p.case else p.case_number}),")
            lines.append('You have to take Homeopathic medicine in the following order:')
            lines.append('')
            lines.append('On first day:')
            for fd in p.first_day_instructions.all():
                base = f"☑ {fd.size_of_bottle} bottle: Labeled as ‘{fd.label}’: take {fd.no_of_pill} pills at {fd.time_of_day}."
                if fd.special_instruction:
                    base = f"☑ {fd.size_of_bottle} bottle: Labeled as ‘{fd.label}’: take {fd.no_of_pill} pills at {fd.time_of_day} {fd.special_instruction}"
                lines.append(base)
            lines.append('')
            lines.append('From Next day onwards:')
            for nd in p.next_day_instructions.all():
                line = f"☑ From Bottle No. {nd.bottle_no}: {nd.no_of_pill} pills at {nd.time_of_day}."
                if nd.special_instruction:
                    line = f"☑ From Bottle No. {nd.bottle_no}: {nd.no_of_pill} pills at {nd.time_of_day} {nd.special_instruction}"
                lines.append(line)
        lines.append('')
        doctor_names = []
        if p.prescribed_by_ami:
            doctor_names.append('Dr. Ami Bhatt')
        if p.prescribed_by_kaushal:
            doctor_names.append('Dr. Kaushal Bhatt')
        if len(doctor_names) == 2:
            lines.append('Dr. Ami Bhatt                Dr. Kaushal Bhatt')
        elif len(doctor_names) == 1:
            lines.append(doctor_names[0])
        else:
            lines.append('Dr. Ami Bhatt                Dr. Kaushal Bhatt')
        
        return lines

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        p = Prescription.objects.get(pk=self.kwargs['pk'])
        
        # Format current prescription
        current_lines = self.format_prescription(p)
        context['formatted'] = "\n".join(current_lines)
        context['prescription'] = p
        
        # Get the stored top margin for this prescription (set at creation)
        context['top_margin_mm'] = p.top_margin_mm
        
        # Calculate current prescription height
        current_prescription_height_mm = p.calculate_printed_height_mm()
        context['current_prescription_height_mm'] = current_prescription_height_mm
        
        # A4 page dimensions
        A4_HEIGHT_MM = 297
        MARGIN_MM = 20
        AVAILABLE_HEIGHT_MM = A4_HEIGHT_MM - (MARGIN_MM * 2)
        MARGIN_GAP_MM = 10
        context['a4_height_mm'] = A4_HEIGHT_MM
        
        # Check if there are previous prescriptions
        previous_prescriptions = Prescription.objects.filter(
            patient=p.patient,
            created_at__lt=p.created_at,
        ).order_by('-created_at')  # Most recent first
        
        has_previous = previous_prescriptions.exists()
        context['has_previous_prescriptions'] = has_previous
        
        # Calculate if there's enough space on the current page.
        # Because `p.top_margin_mm` is stored RELATIVE to the printable area (0..AVAILABLE_HEIGHT_MM),
        # we check against `AVAILABLE_HEIGHT_MM`.
        has_space_on_current_page = (p.top_margin_mm + current_prescription_height_mm) <= AVAILABLE_HEIGHT_MM

        # Show the modal (choice option) only if:
        # 1. There are previous prescriptions AND
        # 2. This prescription fits on the current page (i.e., there IS space available)
        context['has_enough_space'] = has_previous and has_space_on_current_page
        
        return context


class PrescriptionGeneratorListView(ListView):
    model = Prescription
    template_name = 'prescription_generator_list.html'
    context_object_name = 'prescriptions'
    paginate_by = 20

    def get_queryset(self):
        qs = Prescription.objects.select_related('patient').order_by('-created_at')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(patient__name__icontains=q) |
                Q(case_number__icontains=q) |
                Q(case__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_prescriptions'] = Prescription.objects.count()
        return context

@login_required
def ajax_patient_list(request):
    """Return rendered HTML of the patient list."""
    patients = Patient.objects.prefetch_related('followups').all().order_by('-appointment_date')
    for patient in patients:
        patient.scheduled_followups_count = patient.followups.filter(status=FollowUp.STATUS_SCHEDULED).count()
    
    html = render_to_string('partials/patient_list_items.html', {'patients': patients})
    return JsonResponse({'html': html})

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")   # whatever your home page is
        else:
            messages.error(request, "Incorrect username or password")

    return render(request, "login.html")
