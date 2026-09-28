from django.test import TestCase
from django.urls import reverse
from .models import Patient

class PatientSearchTests(TestCase):
    def setUp(self):
        # create some patients to search against
        self.p1 = Patient.objects.create(case='A1', name='Alice Smith', age=30, phone_no='1234567890', doctor='dr_1')
        self.p2 = Patient.objects.create(case='B2', name='Bob Stone', age=40, phone_no='9876543210', doctor='dr_1')
        self.p3 = Patient.objects.create(case='C3', name='Charlie', age=25, phone_no='1230000000', doctor='dr_1')

    def test_search_by_name(self):
        resp = self.client.get(reverse('Anand_Clinic:patient_list') + '?search=Alice')
        self.assertContains(resp, self.p1.name)
        self.assertNotContains(resp, self.p2.name)

    def test_search_by_case_no(self):
        # searching by auto-assigned case_no should return the correct patient
        resp = self.client.get(reverse('Anand_Clinic:patient_list') + f'?search={self.p1.case_no}')
        self.assertContains(resp, self.p1.name)
        self.assertNotContains(resp, self.p2.name)

    def test_search_by_phone_substring(self):
        # phone substring '123' should match p1 and p3
        resp = self.client.get(reverse('Anand_Clinic:patient_list') + '?search=123')
        self.assertContains(resp, self.p1.name)
        self.assertContains(resp, self.p3.name)
        self.assertNotContains(resp, self.p2.name)

    def test_patient_list_hides_home_toolbar(self):
        # The dedicated patient list page should hide the home page toolbar to avoid duplicate/conflicting search UIs
        resp = self.client.get(reverse('Anand_Clinic:patient_list'))
        self.assertNotContains(resp, 'id="patientSearch"')
        # ensure the server-side search field is present
        self.assertContains(resp, 'name="search"')

