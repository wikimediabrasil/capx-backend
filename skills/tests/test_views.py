import secrets
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser
from skills.models import Skill
from skills.serializers import SkillSerializer

class SkillViewSetTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.user.is_staff = True
        self.user.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        skill = {
            'skill_wikidata_item': "Q123456789"
        }
        self.client.post('/skill/', skill)

    def test_get_skills_list(self):
        response = self.client.get('/skill/')
        skills = Skill.objects.all()
        serializer = SkillSerializer(skills, many=True)
        self.assertEqual(response.data['results'], serializer.data)

    def test_get_skill_detail(self):
        response = self.client.get('/skill/1/')
        skills = Skill.objects.all()
        serializer = SkillSerializer(skills.first())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_skill(self):
        skill = {
            'skill_wikidata_item': "Q987654321"
        }
        response = self.client.post('/skill/', skill)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        skill = Skill.objects.get(skill_wikidata_item='Q987654321')
        serializer = SkillSerializer(skill)
        self.assertEqual(response.data, serializer.data)

        options_response = self.client.options('/skill/1/')
        expected_choices = [{'value': 1, 'display_name': 'Q123456789'}, {'value': 2, 'display_name': 'Q987654321'}]
        self.assertEqual(options_response.status_code, status.HTTP_200_OK)
        self.assertEqual(options_response.data['actions']['PUT']['skill_type']['choices'], expected_choices)

    def test_create_skill_nostaff(self):
        self.user.is_staff = False
        self.user.save()
        skill = {
            'skill_wikidata_item': "Q987654321"
        }
        response = self.client.post('/skill/', skill)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_skill(self):
        skill = Skill.objects.get(skill_wikidata_item='Q123456789')
        updated_data = {
            'skill_wikidata_item': 'Q123456780',
        }
        response = self.client.put('/skill/' + str(skill.pk) + '/', updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        skill.refresh_from_db()
        serializer = SkillSerializer(skill)
        self.assertEqual(serializer.data['skill_wikidata_item'], updated_data['skill_wikidata_item'])

    def test_update_skill_nostaff(self):
        self.user.is_staff = False
        self.user.save()
        skill = Skill.objects.get(skill_wikidata_item='Q123456789')
        updated_data = {
            'skill_wikidata_item': 'Q123456780',
        }
        response = self.client.put('/skill/' + str(skill.pk) + '/', updated_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_skill(self):
        skill = Skill.objects.get(skill_wikidata_item='Q123456789')
        updated_data = {
            'skill_wikidata_item': 'Q123456780',
        }
        response = self.client.patch('/skill/' + str(skill.pk) + '/', updated_data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_skill(self):
        response = self.client.delete('/skill/1/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_skill_nostaff(self):
        self.user.is_staff = False
        self.user.save()
        response = self.client.delete('/skill/1/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_skill_referenced(self):
        # Create a second skill that references the first skill
        skill = {
            'skill_wikidata_item': "Q987654321",
            'skill_type': 1
        }
        self.client.post('/skill/', skill)
        response = self.client.delete('/skill/1/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class SkillByTypeTestCase(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='test', password=str(secrets.randbits(16)))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        first = Skill.objects.create(skill_wikidata_item='Q123456789')
        second = Skill.objects.create(skill_wikidata_item='Q987654321')
        second.skill_type.add(first)

    def test_get_skills_by_type(self):
        response = self.client.get('/skills_by_type/1/')
        skills = Skill.objects.filter(skill_type=1)
        serializer = SkillSerializer(skills, many=True)
        expected_data = {item['id']: item['skill_wikidata_item'] for item in serializer.data}
        self.assertEqual(response.data, expected_data)

    def test_get_skills_by_type_empty(self):
        response = self.client.get('/skills_by_type/2/')
        self.assertEqual(response.data, {})

    def test_get_skills_by_type_invalid(self):
        response = self.client.get('/skills_by_type/invalid/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_skills_by_type_root(self):
        response = self.client.get('/skills_by_type/0/')
        skills = Skill.objects.filter(skill_type__isnull=True)
        serializer = SkillSerializer(skills, many=True)
        expected_data = {item['id']: item['skill_wikidata_item'] for item in serializer.data}
        self.assertEqual(response.data, expected_data)

    def test_get_skills_by_type_not_provided(self):
        response = self.client.get('/skills_by_type/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)