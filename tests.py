import unittest
import json
from unittest.mock import patch

from app import app
from models import Company

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_status_endpoint(self):
        """Test API status endpoint returns 200."""
        response = self.app.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'online')

    @patch('routes.run_async_with_retry')
    def test_missing_input_validation(self, mock_run):
        """Test missing input payload is gracefully handled as 400."""
        response = self.app.post('/api/company', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    @patch('routes.run_async_with_retry')
    def test_mocked_company_success(self, mock_run):
        """Test deep successful extraction path via mock."""
        mock_run.return_value = Company(name="Test Corp", industry="Tech")
        
        response = self.app.post('/api/company', json={"company_slug": "test-corp"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["name"], "Test Corp")
        self.assertEqual(data["industry"], "Tech")

    @patch('routes.run_async_with_retry')
    def test_global_error_handler(self, mock_run):
        """Test unhandled internal errors trigger 500 JSON, not crashing."""
        mock_run.side_effect = Exception("Simulated fatal timeout")
        
        response = self.app.post('/api/company', json={"company_slug": "test-error"})
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "error")
        self.assertIn("Internal Server Error", data["error"])

if __name__ == '__main__':
    unittest.main()
