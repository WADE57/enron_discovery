from django.test import TestCase

# Create your tests here.
from datetime import timedelta

from django.contrib.postgres.search import SearchVector
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Email, Employee, Folder


class EnronViewsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.folder = Folder.objects.create(name="inbox")

        cls.alice = Employee.objects.create(name="Alice", email="alice@enron.com")
        cls.bob = Employee.objects.create(name="Bob", email="bob@enron.com")
        cls.charlie = Employee.objects.create(name="Charlie", email="charlie@enron.com")

        now = timezone.now()

        # Root email for thread
        cls.root_email = Email.objects.create(
            message_id="<msg-root@enron>",
            date=now - timedelta(days=3),
            subject="Energy strategy Q1",
            body="Discussion about market strategy and energy contracts.",
            from_employee=cls.alice,
            folder=cls.folder,
        )
        cls.root_email.to_employees.add(cls.bob)

        # Reply 1
        cls.reply_1 = Email.objects.create(
            message_id="<msg-reply-1@enron>",
            date=now - timedelta(days=2),
            subject="Re: Energy strategy Q1",
            body="I agree with the proposed market strategy.",
            from_employee=cls.bob,
            folder=cls.folder,
            in_reply_to=cls.root_email,
        )
        cls.reply_1.to_employees.add(cls.alice)

        # Reply 2 (child of reply_1)
        cls.reply_2 = Email.objects.create(
            message_id="<msg-reply-2@enron>",
            date=now - timedelta(days=1),
            subject="Re: Energy strategy Q1 - follow-up",
            body="Adding legal review and compliance checks.",
            from_employee=cls.charlie,
            folder=cls.folder,
            in_reply_to=cls.reply_1,
        )
        cls.reply_2.to_employees.add(cls.alice, cls.bob)

        # Unrelated email
        cls.other_email = Email.objects.create(
            message_id="<msg-other@enron>",
            date=now,
            subject="Cafeteria menu",
            body="Lunch options for next week.",
            from_employee=cls.charlie,
            folder=cls.folder,
        )
        cls.other_email.to_employees.add(cls.alice)

        # Populate search_vector for FTS tests
        Email.objects.all().update(search_vector=SearchVector("subject", "body"))

    def test_home_page(self):
        response = self.client.get(reverse("enron:home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_emails", response.context)
        self.assertIn("total_employees", response.context)
        self.assertEqual(response.context["total_emails"], 4)

    def test_dashboard_page(self):
        response = self.client.get(reverse("enron:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("chart_labels", response.context)
        self.assertIn("chart_values", response.context)
        self.assertIn("top_senders", response.context)

    def test_search_by_keyword_fts(self):
        response = self.client.get(reverse("enron:search_emails"), {"q": "strategy"})
        self.assertEqual(response.status_code, 200)

        emails = response.context["emails"]
        ids = {e.id for e in emails}

        self.assertIn(self.root_email.id, ids)
        self.assertIn(self.reply_1.id, ids)
        self.assertIn(self.reply_2.id, ids)
        self.assertNotIn(self.other_email.id, ids)

    def test_search_by_sender(self):
        response = self.client.get(
            reverse("enron:search_emails"),
            {"sender": "charlie@enron.com"},
        )
        self.assertEqual(response.status_code, 200)

        emails = response.context["emails"]
        ids = {e.id for e in emails}

        self.assertIn(self.reply_2.id, ids)
        self.assertIn(self.other_email.id, ids)
        self.assertNotIn(self.root_email.id, ids)

    def test_search_without_filters_returns_paginated_results(self):
        response = self.client.get(reverse("enron:search_emails"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context["total_results"]), "4")
        self.assertTrue(response.context["search_hint"])
        self.assertTrue(response.context["enable_pagination"])
        self.assertEqual(response.context["current_page"], 1)

        emails = response.context["emails"]
        ids = {e.id for e in emails}
        self.assertIn(self.root_email.id, ids)
        self.assertIn(self.reply_1.id, ids)
        self.assertIn(self.reply_2.id, ids)
        self.assertIn(self.other_email.id, ids)

    def test_search_by_date_range(self):
        date_from = (timezone.now() - timedelta(days=2)).date().isoformat()
        response = self.client.get(
            reverse("enron:search_emails"),
            {"date_from": date_from},
        )
        self.assertEqual(response.status_code, 200)

        emails = response.context["emails"]
        ids = {e.id for e in emails}

        self.assertIn(self.reply_1.id, ids)
        self.assertIn(self.reply_2.id, ids)
        self.assertIn(self.other_email.id, ids)
        self.assertNotIn(self.root_email.id, ids)

    def test_thread_detail_builds_full_conversation(self):
        response = self.client.get(
            reverse("enron:thread_detail", args=[self.reply_2.id])
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["root"].id, self.root_email.id)
        conversation_ids = [e.id for e in response.context["conversation"]]
        self.assertEqual(
            conversation_ids,
            [self.root_email.id, self.reply_1.id, self.reply_2.id],
        )

    def test_influence_graph(self):
        response = self.client.get(reverse("enron:influence_graph"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("connections", response.context)

        connections = list(response.context["connections"])
        # Verify at least one expected edge exists
        has_alice_to_bob = any(
            c["from_employee__email"] == "alice@enron.com"
            and c["to_employees__email"] == "bob@enron.com"
            for c in connections
        )
        self.assertTrue(has_alice_to_bob)

    def test_email_list_page(self):
        response = self.client.get(reverse("enron:email_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("emails", response.context)
        self.assertIn("stats", response.context)
        self.assertEqual(response.context["stats"]["total_emails"], 4)