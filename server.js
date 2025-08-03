const express = require('express');
const fs = require('fs');
const app = express();
const PORT = 3000;

const timetable = JSON.parse(fs.readFileSync('./timetable.json', 'utf-8'));

const periodTimes = [
  { period: '1st', start: '09:20', end: '10:00' },
  { period: '2nd', start: '10:00', end: '10:40' },
  { period: '3rd', start: '10:40', end: '11:20' },
  { period: 'LUNCH', start: '11:20', end: '11:40' },
  { period: '4th', start: '11:40', end: '12:20' },
  { period: '5th', start: '12:20', end: '13:00' },
  { period: 'SHORT_BREAK', start: '13:00', end: '13:10' },
  { period: '6th', start: '13:10', end: '13:50' },
  { period: '7th', start: '13:50', end: '14:30' }
];

function getCurrentPeriod() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  const timeNow = `${hours}:${minutes}`;

  for (let p of periodTimes) {
    if (timeNow >= p.start && timeNow < p.end) return p.period;
  }
  return null;
}

app.get('/current-period', (req, res) => {
  const className = req.query.class;
  if (!className || !timetable[className]) {
    return res.status(400).json({ error: 'Invalid or missing class name.' });
  }

  const now = new Date();
  const day = now.toLocaleDateString('en-US', { weekday: 'long', timeZone: 'Asia/Kolkata' }).toUpperCase();
  const time = now.toTimeString().slice(0, 5);

  const currentPeriod = getCurrentPeriod();

  if (!currentPeriod) {
    return res.json({
      class: className,
      day,
      time,
      period: null,
      message: 'No active class period now.'
    });
  }

  if (currentPeriod === 'LUNCH' || currentPeriod === 'SHORT_BREAK') {
    return res.json({
      class: className,
      day,
      time,
      period: currentPeriod,
      message: currentPeriod === 'LUNCH' ? 'It is Lunch Break 🍱' : 'It is Short Break ☕'
    });
  }

  const subject = timetable[className][day]?.[currentPeriod] || 'No class';

  res.json({
    class: className,
    day,
    time,
    period: currentPeriod,
    subject
  });
});

app.listen(PORT, () => {
  console.log(`✅ Server running at http://localhost:${PORT}`);
});
