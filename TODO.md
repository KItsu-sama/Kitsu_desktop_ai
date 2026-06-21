# TODO

## Health gateway fixes/diagnostics
- [ ] Add request logging to `do_POST` in `application/health_gateway.py`.
- [ ] Implement `do_OPTIONS` in `application/health_gateway.py` (204 + CORS headers).
- [ ] Add unit tests in `tests/test_health_gateway.py` to verify routing:
  - [x] POST `/chat` returns 501
  - [x] POST unknown path returns 404
  - [x] OPTIONS `/chat` returns 204


