import unittest
from telegram_alerts import message
class TelegramChecks(unittest.TestCase):
 def test_alert_boundary_and_honest_recommendation(self):
  item=dict(name="Engine 034",id="demo",last_cycle=203,priority="Critical",rul=6.9)
  self.assertIn("Replacement: not established",message(item))
  self.assertIn("recorded FD001",message(item))
  self.assertIsNone(message({**item,"rul":31}))
  self.assertIsNone(message({**item,"rul":None}))

 def test_html_format_and_escape(self):
  text=message(dict(name="Machine <34> & demo",id="demo<id>",last_cycle=203,priority="Critical",rul=6.9))
  self.assertIn("<b>Machine: Machine &lt;34&gt; &amp; demo</b>",text)
  self.assertIn("<code>demo&lt;id&gt;</code>",text)
  self.assertIn("<b>Priority: Critical</b>",text)
  self.assertIn("<b>Predicted remaining life: 6.9 cycles</b>",text)
  self.assertIn("Random Forest",text)
