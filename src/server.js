require('dotenv').config();
const express = require('express');
const cors = require('cors');

const apiRoutes = require('./routes/api');

const app = express();
const port = process.env.PORT || 4000;

app.use(cors({ origin: process.env.FRONTEND_URL || 'http://localhost:5173', credentials: true }));
app.use(express.json({ limit: '2mb' }));
app.use('/api', apiRoutes);

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', service: 'CiteVerify API', verificationMode: 'extraction-only' });
});

app.use((err, _req, res, _next) => {
  const status = ['InvalidPDFException', 'PasswordException'].includes(err.name)
    ? 422
    : err.name === 'MulterError'
    ? (err.code === 'LIMIT_FILE_SIZE' ? 413 : 400)
    : err.status || 500;
  if (status >= 500) console.error(err);
  res.status(status).json({ error: status >= 500 ? 'Internal server error' : err.message });
});

app.listen(port, () => console.log(`CiteVerify API listening on http://localhost:${port}`));
