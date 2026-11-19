const path = require('path');

if (process.env.NODE_ENV === 'production' && (!process.env.JWT_SECRET || process.env.JWT_SECRET === 'replace-with-a-long-random-secret')) {
  throw new Error('JWT_SECRET must be set in production');
}

module.exports = {
  dataDir: process.env.DATA_DIR ? path.resolve(process.env.DATA_DIR) : path.join(__dirname, '..', '..', 'data'),
  uploadDir: process.env.UPLOAD_DIR ? path.resolve(process.env.UPLOAD_DIR) : path.join(__dirname, '..', '..', 'uploads'),
  jwtSecret: process.env.JWT_SECRET || 'development-only-change-me',
};
