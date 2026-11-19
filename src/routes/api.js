const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const auth = require('../middleware/auth');
const store = require('../models/store');
const { jwtSecret, uploadDir } = require('../config/config');
const { id } = require('../utils/crypto');
const { fileToText } = require('../services/pdfService');
const { buildReport } = require('../services/verificationService');

const router = express.Router();
fs.mkdirSync(uploadDir, { recursive: true });

const upload = multer({
  dest: uploadDir,
  limits: { fileSize: 20 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ok = file.mimetype === 'application/pdf' || path.extname(file.originalname).toLowerCase() === '.pdf';
    if (!ok) {
      const error = new Error('Only PDF documents are accepted');
      error.status = 400;
      cb(error);
      return;
    }
    cb(null, true);
  },
});

router.post('/auth/register', (req, res) => {
  const body = req.body && typeof req.body === 'object' ? req.body : {};
  const name = typeof body.name === 'string' ? body.name.trim() : '';
  const email = typeof body.email === 'string' ? body.email.trim().toLowerCase() : '';
  const password = typeof body.password === 'string' ? body.password : '';
  if (!name || name.length > 100 || email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || password.length < 8 || password.length > 128) {
    return res.status(400).json({ error: 'Name, valid email, and an 8- to 128-character password are required' });
  }
  const users = store.users();
  if (users.some(user => user.email.toLowerCase() === email)) {
    return res.status(409).json({ error: 'An account with this email already exists' });
  }
  const user = { id: id('user'), name, email, passwordHash: bcrypt.hashSync(password, 10) };
  users.push(user);
  store.saveUsers(users);
  const token = jwt.sign({ id: user.id, name: user.name, email: user.email }, jwtSecret, { expiresIn: '7d' });
  res.status(201).json({ token, user: { id: user.id, name: user.name, email: user.email } });
});

router.post('/auth/login', (req, res) => {
  const body = req.body && typeof req.body === 'object' ? req.body : {};
  const email = typeof body.email === 'string' ? body.email.trim().toLowerCase() : '';
  const password = typeof body.password === 'string' ? body.password : '';
  if (!email || !password || email.length > 254 || password.length > 128) return res.status(400).json({ error: 'Valid email and password are required' });
  const user = store.users().find(item => item.email.toLowerCase() === email);
  if (!user || !bcrypt.compareSync(password, user.passwordHash)) {
    return res.status(401).json({ error: 'Invalid email or password' });
  }
  const token = jwt.sign({ id: user.id, name: user.name, email: user.email }, jwtSecret, { expiresIn: '7d' });
  res.json({ token, user: { id: user.id, name: user.name, email: user.email } });
});

router.get('/auth/me', auth, (req, res) => res.json({ user: req.user }));

router.post('/documents', auth, upload.single('file'), async (req, res, next) => {
  try {
    if (!req.file) return res.status(400).json({ error: 'A PDF file is required' });
    const text = await fileToText(req.file.path);
    const report = buildReport(req.file.originalname, text);
    const document = {
      id: id('doc'),
      userId: req.user.id,
      fileName: req.file.originalname,
      uploadedAt: new Date().toISOString(),
      status: 'COMPLETED',
      report,
    };
    const documents = store.documents();
    documents.unshift(document);
    store.saveDocuments(documents);
    res.status(201).json(document);
  } catch (error) {
    next(error);
  } finally {
    if (req.file) {
      try {
        await fs.promises.unlink(req.file.path);
      } catch (error) {
        if (error.code !== 'ENOENT') console.error('Failed to remove processed upload:', error);
      }
    }
  }
});

router.get('/documents', auth, (req, res) => {
  const documents = store.documents().filter(doc => doc.userId === req.user.id);
  res.json({ documents });
});

router.get('/documents/:documentId', auth, (req, res) => {
  const document = store.documents().find(doc => doc.id === req.params.documentId && doc.userId === req.user.id);
  if (!document) return res.status(404).json({ error: 'Document not found' });
  res.json(document);
});

router.get('/dashboard', auth, (req, res) => {
  const documents = store.documents().filter(doc => doc.userId === req.user.id);
  const claims = documents.flatMap(doc => doc.report.claims);
  res.json({
    totalDocuments: documents.length,
    totalClaims: claims.length,
    supported: claims.filter(claim => claim.status === 'SUPPORTED').length,
    partiallySupported: claims.filter(claim => claim.status === 'PARTIALLY SUPPORTED').length,
    unsupported: claims.filter(claim => claim.status === 'UNSUPPORTED').length,
    contradicted: claims.filter(claim => claim.status === 'CONTRADICTED').length,
    unverifiable: claims.filter(claim => claim.status === 'UNVERIFIABLE').length,
    recentDocuments: documents.slice(0, 5),
  });
});

router.get('/documents/:documentId/report', auth, (req, res) => {
  const document = store.documents().find(doc => doc.id === req.params.documentId && doc.userId === req.user.id);
  if (!document) return res.status(404).json({ error: 'Document not found' });
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="${document.fileName.replace(/[^a-z0-9.-]/gi, '_')}-citeverify.txt"`);
  const lines = [
    'CiteVerify Analysis Report',
    `Document: ${document.fileName}`,
    `Processed: ${document.uploadedAt}`,
    '',
    'Summary',
    document.report.summary,
    '',
    ...document.report.claims.flatMap(claim => [
      `Claim: ${claim.text}`,
      `Status: ${claim.status}`,
      `Evidence: ${claim.evidence}`,
      `Explanation: ${claim.explanation}`,
      `Limitations: ${claim.limitations.join('; ')}`,
      '',
    ]),
  ];
  res.send(lines.join('\n'));
});

module.exports = router;
