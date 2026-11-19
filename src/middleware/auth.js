const jwt = require('jsonwebtoken');
const { jwtSecret } = require('../config/config');

module.exports = function auth(req, res, next) {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) return res.status(401).json({ error: 'Authentication required' });
  try {
    req.user = jwt.verify(header.slice(7), jwtSecret);
    next();
  } catch {
    res.status(401).json({ error: 'Invalid or expired session' });
  }
};
