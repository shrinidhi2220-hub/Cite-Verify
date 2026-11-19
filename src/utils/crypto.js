const crypto = require('crypto');

module.exports = {
  id: prefix => `${prefix}_${crypto.randomBytes(10).toString('hex')}`,
};
