'use strict';

const { Router } = require('express');
const { getAllUsers, getUserCount, getOptedInUsers } = require('../../db/users.db');

const router = Router();

router.get('/', (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit || '50', 10), 200);
    const offset = parseInt(req.query.offset || '0', 10);
    const users = getAllUsers({ limit, offset });
    const total = getUserCount();
    res.json({
      users,
      pagination: { total, limit, offset, hasMore: offset + limit < total }
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/opted-in', (req, res) => {
  try {
    const users = getOptedInUsers();
    res.json({ users, count: users.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
