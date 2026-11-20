#!/usr/bin/env python3
"""Mock server for the Ali Attendance API (ag_rest_api, Odoo 18).

Serves all 72 endpoints with the same example responses as the
documentation at https://ghozali25.github.io/mobile_absensi_odoo/api/
No dependencies beyond the Python standard library.

Usage:
    python3 mock-server.py            # http://localhost:8072
    python3 mock-server.py 8080       # custom port

Auth behaviour mirrors the real API:
  - POST /ag_rest_api/v1/auth/token accepts any db/login/password and
    returns a demo Bearer token.
  - Every other endpoint requires an Authorization: Bearer <token> header
    (any non-empty token is accepted by the mock). Missing header -> 401
    {"status": "error", "code": "NO_TOKEN", ...} — same as the real API.
  - POST /ag_rest_api/v1/auth/logout accepts any token.
"""
import base64
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MOCKS = {'/ag_rest_api/v1/announcement/detail': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'id': 1, 'title': 'Uji Pengumuman', 'body_html': '<p>Isi pengumuman uji.</p>', 'body_text': 'Isi pengumuman uji.', 'publish_date': '2026-10-26', 'release_date': None, 'expiry_date': None, 'pinned': True, 'is_dibaca': False, 'has_image': False}}}, '/ag_rest_api/v1/announcement/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'count': 1, 'items': [{'id': 1, 'title': 'Uji Pengumuman', 'body': '<p>Isi pengumuman uji.</p>', 'publish_date': None, 'pinned': True}]}}}, '/ag_rest_api/v1/announcement/mark_read': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengumuman ditandai sudah dibaca.', 'data': {'marked': True}}}, '/ag_rest_api/v1/approvals/act': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Berhasil diproses.', 'data': {'leave': {'id': 5, 'state': 'validate'}}}}, '/ag_rest_api/v1/approvals/history': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'count': 2, 'items': [{'id': 5, 'type': {'id': 2, 'name': 'Sick Time Off'}, 'date_from': '2026-12-07 00:00:00', 'date_to': '2026-12-08 23:59:59', 'number_of_days': 2.0, 'state': 'validate', 'state_label': 'Approved', 'tipe': 'cuti'}, {'id': 1, 'tipe': 'lembur', 'tanggal': '2026-10-26', 'tanggal_lembur': '2026-10-26', 'tanggal_selesai': '2026-10-26', 'date_to': '2026-10-26 20:00:00', 'jam': 2.0, 'jam_mulai': '18:00', 'jam_selesai': '20:00', 'proposed_hours': 2.0, 'approved_hours': 2.0, 'upah': 100000, 'hrms_amount': 100000, 'overtime_type': 'weekday', 'state': 'approved', 'status_app': 'disetujui', 'employee_id': 15, 'employee_name': 'AG Test'}]}}}, '/ag_rest_api/v1/approvals/inbox': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'count': 1, 'items': [{'id': 5, 'employee_name': 'AG Test', 'type': {'id': 2, 'name': 'Sick Time Off'}, 'state': 'confirm'}]}}}, '/ag_rest_api/v1/attendance-request/cancel': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan absensi dibatalkan.', 'data': {'id': 1}}}, '/ag_rest_api/v1/attendance-request/detail': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'id': 1, 'pengajuan_id': 1, 'tipe': 'attendance_request', 'kategori': 'attendance_request', 'modul': 'attendance_request', 'request_date': '2026-11-05', 'tanggal': '2026-11-05', 'date': '2026-11-05', 'check_in_time': '08:00', 'jam_masuk': '08:00', 'check_in': '08:00', 'check_out_time': '17:00', 'jam_pulang': '17:00', 'check_out': '17:00', 'check_in_float': 8.0, 'check_out_float': 17.0, 'reason': 'Lupa absen masuk', 'alasan': 'Lupa absen masuk', 'keterangan': 'Lupa absen masuk', 'state': 'menunggu', 'status': 'menunggu', 'status_app': 'menunggu', 'rejection_reason': '', 'alasan_tolak': '', 'refuse_reason': '', 'catatan_penolakan': '', 'employee_id': 15, 'employee_name': 'AG Test', 'pemohon': {'nama': 'AG Test', 'jabatan': 'Staff', 'departemen': 'HR', 'nip': '46021'}, 'create_date': '2026-11-05 02:00:00', 'attendance_id': False, 'approver_id': False, 'approver_name': '', 'item': {'id': 1, 'pengajuan_id': 1, 'tipe': 'attendance_request', 'kategori': 'attendance_request', 'modul': 'attendance_request', 'request_date': '2026-11-05', 'tanggal': '2026-11-05', 'date': '2026-11-05', 'check_in_time': '08:00', 'jam_masuk': '08:00', 'check_in': '08:00', 'check_out_time': '17:00', 'jam_pulang': '17:00', 'check_out': '17:00', 'check_in_float': 8.0, 'check_out_float': 17.0, 'reason': 'Lupa absen masuk', 'alasan': 'Lupa absen masuk', 'keterangan': 'Lupa absen masuk', 'state': 'menunggu', 'status': 'menunggu', 'status_app': 'menunggu', 'rejection_reason': '', 'alasan_tolak': '', 'refuse_reason': '', 'catatan_penolakan': '', 'employee_id': 15, 'employee_name': 'AG Test', 'pemohon': {'nama': 'AG Test', 'jabatan': 'Staff', 'departemen': 'HR', 'nip': '46021'}, 'create_date': '2026-11-05 02:00:00', 'attendance_id': False, 'approver_id': False, 'approver_name': ''}, 'request': {'id': 1, 'pengajuan_id': 1, 'tipe': 'attendance_request', 'kategori': 'attendance_request', 'modul': 'attendance_request', 'request_date': '2026-11-05', 'tanggal': '2026-11-05', 'date': '2026-11-05', 'check_in_time': '08:00', 'jam_masuk': '08:00', 'check_in': '08:00', 'check_out_time': '17:00', 'jam_pulang': '17:00', 'check_out': '17:00', 'check_in_float': 8.0, 'check_out_float': 17.0, 'reason': 'Lupa absen masuk', 'alasan': 'Lupa absen masuk', 'keterangan': 'Lupa absen masuk', 'state': 'menunggu', 'status': 'menunggu', 'status_app': 'menunggu', 'rejection_reason': '', 'alasan_tolak': '', 'refuse_reason': '', 'catatan_penolakan': '', 'employee_id': 15, 'employee_name': 'AG Test', 'pemohon': {'nama': 'AG Test', 'jabatan': 'Staff', 'departemen': 'HR', 'nip': '46021'}, 'create_date': '2026-11-05 02:00:00', 'attendance_id': False, 'approver_id': False, 'approver_name': ''}}}}, '/ag_rest_api/v1/attendance-request/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'count': 1, 'total': 1, 'items': [{'id': 1, 'pengajuan_id': 1, 'tipe': 'attendance_request', 'kategori': 'attendance_request', 'modul': 'attendance_request', 'request_date': '2026-11-05', 'tanggal': '2026-11-05', 'date': '2026-11-05', 'check_in_time': '08:00', 'jam_masuk': '08:00', 'check_in': '08:00', 'check_out_time': '17:00', 'jam_pulang': '17:00', 'check_out': '17:00', 'check_in_float': 8.0, 'check_out_float': 17.0, 'reason': 'Lupa absen masuk', 'alasan': 'Lupa absen masuk', 'keterangan': 'Lupa absen masuk', 'state': 'menunggu', 'status': 'menunggu', 'status_app': 'menunggu', 'rejection_reason': '', 'alasan_tolak': '', 'refuse_reason': '', 'catatan_penolakan': '', 'employee_id': 15, 'employee_name': 'AG Test', 'pemohon': {'nama': 'AG Test', 'jabatan': 'Staff', 'departemen': 'HR', 'nip': '46021'}, 'create_date': '2026-11-05 02:00:00', 'attendance_id': False, 'approver_id': False, 'approver_name': ''}], 'has_more': False}}}, '/ag_rest_api/v1/attendance-request/submit': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan absensi terkirim.', 'data': {'id': 1, 'pengajuan_id': 1, 'tipe': 'attendance_request', 'kategori': 'attendance_request', 'modul': 'attendance_request', 'request_date': '2026-11-05', 'tanggal': '2026-11-05', 'date': '2026-11-05', 'check_in_time': '08:00', 'jam_masuk': '08:00', 'check_in': '08:00', 'check_out_time': '17:00', 'jam_pulang': '17:00', 'check_out': '17:00', 'check_in_float': 8.0, 'check_out_float': 17.0, 'reason': 'Lupa absen masuk', 'alasan': 'Lupa absen masuk', 'keterangan': 'Lupa absen masuk', 'state': 'menunggu', 'status': 'menunggu', 'status_app': 'menunggu', 'rejection_reason': '', 'alasan_tolak': '', 'refuse_reason': '', 'catatan_penolakan': '', 'employee_id': 15, 'employee_name': 'AG Test', 'pemohon': {'nama': 'AG Test', 'jabatan': 'Staff', 'departemen': 'HR', 'nip': '46021'}, 'create_date': '2026-11-05 02:00:00', 'attendance_id': False, 'approver_id': False, 'approver_name': '', 'request': {'id': 1, 'pengajuan_id': 1, 'tipe': 'attendance_request', 'kategori': 'attendance_request', 'modul': 'attendance_request', 'request_date': '2026-11-05', 'tanggal': '2026-11-05', 'date': '2026-11-05', 'check_in_time': '08:00', 'jam_masuk': '08:00', 'check_in': '08:00', 'check_out_time': '17:00', 'jam_pulang': '17:00', 'check_out': '17:00', 'check_in_float': 8.0, 'check_out_float': 17.0, 'reason': 'Lupa absen masuk', 'alasan': 'Lupa absen masuk', 'keterangan': 'Lupa absen masuk', 'state': 'menunggu', 'status': 'menunggu', 'status_app': 'menunggu', 'rejection_reason': '', 'alasan_tolak': '', 'refuse_reason': '', 'catatan_penolakan': '', 'employee_id': 15, 'employee_name': 'AG Test', 'pemohon': {'nama': 'AG Test', 'jabatan': 'Staff', 'departemen': 'HR', 'nip': '46021'}, 'create_date': '2026-11-05 02:00:00', 'attendance_id': False, 'approver_id': False, 'approver_name': ''}}}}, '/ag_rest_api/v1/attendance/break': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Waktu istirahat berhasil dicatat.', 'data': {}}}, '/ag_rest_api/v1/attendance/clock-in': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Clock-in tercatat.', 'data': {'attendance': {'id': 12, 'check_in': '2026-10-26 01:00:00', 'check_out': None, 'worked_hours': 0.0, 'distance_in_m': 12.4, 'location': {'id': 1, 'name': 'Kantor Pusat'}}}}}, '/ag_rest_api/v1/attendance/clock-out': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Clock-out tercatat.', 'data': {'attendance': {'id': 12, 'check_in': '2026-10-26 01:00:00', 'check_out': '2026-10-26 10:00:00', 'worked_hours': 9.0}}}}, '/ag_rest_api/v1/attendance/history': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 12, 'check_in': '2026-10-26 01:00:00', 'check_out': '2026-10-26 10:00:00', 'worked_hours': 9.0}]}}}, '/ag_rest_api/v1/attendance/photo/<attendance_id>/<kind>': {'method': 'GET', 'token': True, 'response_success': 'binary image/jpeg'}, '/ag_rest_api/v1/attendance/status': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'checked_in': False, 'open_attendance': None}}}, '/ag_rest_api/v1/auth/change-password': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Kata sandi berhasil diubah.', 'data': {}}}, '/ag_rest_api/v1/auth/logout': {'method': 'POST', 'token': False, 'response_success': {'status': 'success', 'message': 'Logout berhasil, token dicabut.', 'data': {}}}, '/ag_rest_api/v1/auth/me': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'user': {'id': 15, 'name': 'AG Test', 'login': 'agtest'}, 'employee': {'id': 194, 'name': 'AG Test', 'job': {'id': 1, 'name': 'Staff'}, 'department': None, 'work_email': 'agtest@example.com', 'is_face_registered': False, 'location_policy': 'wfo', 'allowed_location_ids': [1], 'allowed_locations': [{'id': 1, 'name': 'Kantor Pusat', 'lat': -6.2, 'lng': 106.8, 'radius_m': 100.0}], 'face_code': ''}}}}, '/ag_rest_api/v1/auth/token': {'method': 'POST', 'token': False, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'token': '<token-mentah-43-karakter>', 'token_type': 'Bearer', 'expires_at': '2026-11-26 02:00:00', 'user': {'id': 15, 'name': 'AG Test', 'login': 'agtest'}}}}, '/ag_rest_api/v1/calendar/schedule': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'hari_kerja': [0, 1, 2, 3, 4], 'hari_libur': [5, 6], 'daftar_shift': [{'name': 'Shift', 'dayofweek': 0, 'hour_from': '08:00', 'hour_to': '17:00', 'day_period': 'morning'}]}}}, '/ag_rest_api/v1/config/public': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'office_lat': -6.2, 'office_lng': 106.8, 'office_radius_m': 100.0, 'features': {}, 'location_policy': 'wfo', 'locations': [{'id': 1, 'name': 'Kantor Pusat', 'lat': -6.2, 'lng': 106.8, 'radius_m': 100.0}, {'id': 2, 'name': 'Kantor Cabang', 'lat': -6.3, 'lng': 107.0, 'radius_m': 150.0}], 'allowed_location_ids': [1]}}}, '/ag_rest_api/v1/dashboard/summary': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'user': {'id': 15, 'name': 'AG Test', 'login': 'agtest'}, 'employee_brief': {'id': 194, 'name': 'AG Test'}, 'employee': {'id': 194, 'name': 'AG Test', 'location_policy': 'wfo', 'allowed_location_ids': [1], 'allowed_locations': [{'id': 1, 'name': 'Kantor Pusat', 'lat': -6.2, 'lng': 106.8, 'radius_m': 100.0}], 'face_code': 'FACE-K7M2QX9P'}, 'attendance': {'checked_in': True, 'open_attendance': {'id': 12, 'check_in': '2026-10-26 01:00:00', 'check_out': None, 'worked_hours': 0.0}}, 'shifts_today': [{'tanggal': '2026-10-26', 'hari': 'Monday', 'nama_shift': 'Shift', 'jam_masuk': '08:00', 'jam_pulang': '17:00', 'is_hari_libur': False}], 'history': [], 'config': {'office_lat': 0.0, 'office_lng': 0.0, 'office_radius_m': 100.0, 'features': {}, 'locations': [{'id': 1, 'name': 'Kantor Pusat', 'lat': -6.2, 'lng': 106.8, 'radius_m': 100.0}, {'id': 2, 'name': 'Kantor Cabang', 'lat': -6.3, 'lng': 107.0, 'radius_m': 150.0}]}, 'server_time': {'timestamp': 1792987782}}}}, '/ag_rest_api/v1/denda/rules': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'aturan_denda_masuk': [{'id': 1, 'rentang': '1 - 15 Menit', 'keterangan': 'Toleransi keterlambatan ringan', 'nominal_formatted': 'Rp 10.000'}], 'aturan_denda_pulang': []}}}, '/ag_rest_api/v1/dinas/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 8, 'kota_tujuan': 'Bandung', 'instansi_tujuan': 'Klien X', 'tanggal_mulai': '2026-12-14', 'tanggal_selesai': '2026-12-15', 'keperluan': 'Bandung - Klien X: Survey', 'status': 'menunggu', 'dokumen_url': None}]}}}, '/ag_rest_api/v1/dinas/request': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan dinas berhasil dikirim.', 'data': {'leave_id': 8}}}, '/ag_rest_api/v1/dokumen/preview': {'method': 'POST', 'token': True, 'response_success': 'binary application/pdf (atau image/* sesuai lampiran)'}, '/ag_rest_api/v1/employee/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'employees': [{'id': 194, 'name': 'AG Test', 'job': 'Staff', 'department': '', 'work_email': 'agtest@example.com', 'photo': '/web/image/hr.employee/194/avatar_128'}]}}}, '/ag_rest_api/v1/employee/photo': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Foto profil berhasil diperbarui.', 'data': {}}}, '/ag_rest_api/v1/employee/photo/<employee_id>': {'method': 'GET', 'token': True, 'response_success': 'binary image/png'}, '/ag_rest_api/v1/employee/profile': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'employee': {'id': 194, 'name': 'AG Test', 'work_email': 'agtest@example.com', 'photo': '/web/image/hr.employee/194/avatar_128'}}}}, '/ag_rest_api/v1/face/enroll': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Wajah terdaftar di server.', 'data': {'is_face_registered': True, 'face_enrolled_at': '2026-10-26 04:00:00', 'face_code': 'FACE-K7M2QX9P'}}}, '/ag_rest_api/v1/face/status': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'is_face_registered': True, 'face_enrolled_at': '2026-10-26 04:00:00', 'face_code': 'FACE-K7M2QX9P'}}}, '/ag_rest_api/v1/face/unregister': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pendaftaran wajah dihapus.', 'data': {'is_face_registered': False, 'face_code': ''}}}, '/ag_rest_api/v1/issue/detail': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'issue': {'id': 1, 'nomor_tiket': 'TKT-202610-0001', 'status': 'menunggu'}}}}, '/ag_rest_api/v1/issue/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 1, 'nomor_tiket': 'TKT-202610-0001', 'kategori_masalah': 'sistem_error', 'judul': 'Uji tiket', 'status': 'menunggu'}]}}}, '/ag_rest_api/v1/issue/submit': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Laporan kendala absensi berhasil dikirim.', 'data': {'id': 1, 'nomor_tiket': 'TKT-202610-0001'}}}, '/ag_rest_api/v1/kpi/latest': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'nilai_akhir': 95.0, 'grade': 'A', 'status': 'Sangat Baik', 'periode': 'October 2026', 'pencapaian': []}}}, '/ag_rest_api/v1/mobile/features': {'method': 'GET', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': [{'code': 'attendance', 'name': 'Absensi', 'active': True}, {'code': 'timeoff', 'name': 'Cuti & Dinas', 'active': True}, {'code': 'overtime', 'name': 'Lembur', 'active': True}, {'code': 'payslip', 'name': 'Slip Gaji', 'active': True}, {'code': 'face', 'name': 'Face Recognition', 'active': True}, {'code': 'approvals', 'name': 'Persetujuan', 'active': True}, {'code': 'announcement', 'name': 'Pengumuman', 'active': True}, {'code': 'reimbursement', 'name': 'Reimbursement', 'active': False}]}}, '/ag_rest_api/v1/overtime/approve': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan lembur disetujui.', 'data': {'overtime': {'id': 1, 'tipe': 'lembur', 'tanggal': '2026-10-26', 'tanggal_lembur': '2026-10-26', 'tanggal_selesai': '2026-10-26', 'date_to': '2026-10-26 20:00:00', 'jam': 2.0, 'jam_mulai': '18:00', 'jam_selesai': '20:00', 'proposed_hours': 2.0, 'approved_hours': 2.0, 'upah': 100000, 'hrms_amount': 100000, 'overtime_type': 'weekday', 'state': 'approved', 'status_app': 'disetujui', 'employee_id': 15, 'employee_name': 'AG Test'}}}}, '/ag_rest_api/v1/overtime/cancel': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan lembur dibatalkan.', 'data': {'overtime': {'id': 1, 'tipe': 'lembur', 'tanggal': '2026-10-26', 'tanggal_lembur': '2026-10-26', 'tanggal_selesai': '2026-10-26', 'date_to': '2026-10-26 20:00:00', 'jam': 2.0, 'jam_mulai': '18:00', 'jam_selesai': '20:00', 'proposed_hours': 2.0, 'approved_hours': 0.0, 'upah': 100000, 'hrms_amount': 100000, 'overtime_type': 'weekday', 'state': 'refused', 'status_app': 'ditolak', 'employee_id': 15, 'employee_name': 'AG Test'}}}}, '/ag_rest_api/v1/overtime/history': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 1, 'date': '2026-10-26', 'name': 'Lembur uji', 'proposed_hours': 2.0, 'approved_hours': 0.0, 'state': 'confirm', 'state_label': 'Menunggu'}]}}}, '/ag_rest_api/v1/overtime/request': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan lembur berhasil dikirim.', 'data': {'id': 1}}}, '/ag_rest_api/v1/payslip/detail': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'payslip': {'id': 3, 'name': 'SLIP/003', 'date_from': '2026-10-01', 'date_to': '2026-10-31', 'state': 'done', 'state_label': 'Selesai', 'gross': 5000000, 'net_pay': 4500000, 'currency': 'IDR', 'lines': [{'name': 'Basic Salary', 'code': 'BASIC', 'category': 'BASIC', 'amount': 5000000}]}}}}, '/ag_rest_api/v1/payslip/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 3, 'name': 'SLIP/003', 'date_from': '2026-10-01', 'date_to': '2026-10-31', 'state': 'done', 'state_label': 'Selesai'}]}}}, '/ag_rest_api/v1/reimbursement/approve': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Berhasil diproses.', 'data': {'sheet_id': 2}}}, '/ag_rest_api/v1/reimbursement/detail': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'expense': {'id': 4, 'name': 'Uji reimburse', 'total_amount': 50000, 'state': 'draft'}}}}, '/ag_rest_api/v1/reimbursement/jenis': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 10, 'name': 'Transport'}]}}}, '/ag_rest_api/v1/reimbursement/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 4, 'name': 'Uji reimburse', 'date': '2026-10-26', 'total_amount': 50000, 'state': 'draft'}]}}}, '/ag_rest_api/v1/reimbursement/submit': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan reimbursement berhasil dikirim.', 'data': {'expense_id': 4, 'sheet_id': 2}}}, '/ag_rest_api/v1/server-time': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'timestamp': 1792987782, 'utc': '2026-10-26 04:09:42', 'user_tz': 'Asia/Jakarta'}}}, '/ag_rest_api/v1/shift/today': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'tanggal': '2026-10-26', 'hari': 'Monday', 'nama_shift': 'Shift', 'jam_masuk': '08:00', 'jam_pulang': '17:00', 'is_hari_libur': False}]}}}, '/ag_rest_api/v1/shift/upcoming': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': []}}}, '/ag_rest_api/v1/subordinates/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'employees': []}}}, '/ag_rest_api/v1/subordinates/month': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'employee': {'id': 195, 'name': 'Bawahan'}, 'attendance': [], 'leaves': []}}}, '/ag_rest_api/v1/swap/cancel': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan tukar shift berhasil dibatalkan.', 'data': {}}}, '/ag_rest_api/v1/swap/colleague-schedule': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'jadwal': []}}}, '/ag_rest_api/v1/swap/count': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'count': 0}}}, '/ag_rest_api/v1/swap/history': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'permintaan_masuk': [], 'pengajuan_saya': [{'id': 3, 'pegawai_tujuan_id': 195, 'status': 'menunggu_rekan', 'status_label': 'Menunggu Rekan'}], 'pending_masuk_count': 0}}}, '/ag_rest_api/v1/swap/init': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'rekan_list': [{'id': 195, 'nama_lengkap': 'Budi', 'jabatan': 'Staff', 'departemen': ''}], 'jadwal_pengaju': [], 'pending_masuk_count': 0}}}, '/ag_rest_api/v1/swap/respond': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Permintaan tukar shift berhasil disetujui.', 'data': {}}}, '/ag_rest_api/v1/swap/submit': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan tukar shift berhasil dikirim ke rekan kerja!', 'data': {'id': 3}}}, '/ag_rest_api/v1/task/detail': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'task': {'id': 1, 'judul': 'Tugas Uji', 'status': 'selesai'}}}}, '/ag_rest_api/v1/task/list': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 1, 'judul': 'Tugas Uji', 'status': 'selesai', 'progres': 100}], 'statistik': {'total_semua': 1, 'total_berjalan': 0, 'total_selesai': 1}}}}, '/ag_rest_api/v1/task/update-status': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Status penugasan berhasil diperbarui.', 'data': {}}}, '/ag_rest_api/v1/team/org-chart': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'tree': [{'id': 1, 'name': 'Administrator', 'job': 'Manager', 'department': 'HR', 'photo': '/ag_rest_api/v1/employee/photo/1', 'manager': '', 'children': [{'id': 15, 'name': 'AG Test', 'job': 'Staff', 'department': 'HR', 'photo': '/ag_rest_api/v1/employee/photo/15', 'manager': 'Administrator', 'children': []}]}], 'me_id': 15}}}, '/ag_rest_api/v1/timeoff/cancel': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan dibatalkan.', 'data': {'leave': {'id': 5, 'type': {'id': 2, 'name': 'Sick Time Off'}, 'date_from': '2026-12-07 00:00:00', 'date_to': '2026-12-08 23:59:59', 'number_of_days': 2.0, 'state': 'cancel', 'state_label': 'Cancelled'}}}}, '/ag_rest_api/v1/timeoff/history': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 5, 'type': {'id': 2, 'name': 'Sick Time Off'}, 'date_from': '2026-12-07 00:00:00', 'date_to': '2026-12-08 23:59:59', 'number_of_days': 2.0, 'state': 'confirm', 'state_label': 'To Approve'}]}}}, '/ag_rest_api/v1/timeoff/request': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'Pengajuan terkirim.', 'data': {'leave': {'id': 5, 'state': 'confirm'}}}}, '/ag_rest_api/v1/timeoff/types': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'items': [{'id': 2, 'name': 'Sick Time Off', 'requires_allocation': False, 'virtual_remaining_leaves': 0}]}}}, '/ag_rest_api/v1/tracking/live': {'method': 'GET', 'token': True, 'response_success': 'text/event-stream: data: {"employee_id": 15, "latitude": -6.2, "longitude": 106.8, "accuracy_m": 12, "battery_level": 80, "mock_detected": false, "create_date": "2026-11-05 02:00:00"}'}, '/ag_rest_api/v1/tracking/ping': {'method': 'POST', 'token': True, 'response_success': {'status': 'success', 'message': 'OK', 'data': {'accepted': True}}}}

# 1x1 transparent PNG, returned by the two photo endpoints.
PNG_1X1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAwMCAO+ip1sAAAAASUVORK5CYII=')

DEMO_TOKEN = 'demo-token-mock-server'
NO_TOKEN = {'status': 'error', 'code': 'NO_TOKEN',
            'message': 'Header Authorization: Bearer <token> wajib diisi.'}


def _match(path):
    """Match a request path against mock templates with <param> slots."""
    if path in MOCKS:
        return MOCKS[path]
    for template, ep in MOCKS.items():
        if '<' not in template:
            continue
        regex = re.sub(r'<[^>]+>', r'[^/]+', template)
        if re.fullmatch(regex, path):
            return ep
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers',
                         'Authorization, Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def _send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def _handle(self):
        path = self.path.split('?', 1)[0].rstrip('/') or '/'
        if path == '/ag_rest_api/v1/auth/token' and self.command == 'POST':
            length = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(length) if length else b'{}'
            try:
                creds = json.loads(body or b'{}')
            except json.JSONDecodeError:
                creds = {}
            self._send_json(200, {
                'status': 'success', 'message': 'Login berhasil (mock).',
                'data': {
                    'token': DEMO_TOKEN,
                    'expires_at': '2099-12-31 23:59:59',
                    'user': {
                        'id': 2,
                        'name': creds.get('login', 'demo'),
                        'email': creds.get('login', 'demo'),
                        'employee_id': 15,
                        'employee_name': 'AG Test',
                    },
                    'db': creds.get('db', 'masterdata'),
                }})
            return
        ep = _match(path)
        if ep is None:
            self._send_json(404, {'status': 'error', 'code': 'NOT_FOUND',
                                  'message': 'Endpoint tidak dikenal mock '
                                             'server: ' + path})
            return
        if ep.get('token', True):
            auth = self.headers.get('Authorization', '')
            if not auth.startswith('Bearer ') or not auth[7:].strip():
                self._send_json(401, NO_TOKEN)
                return
        if ep.get('method') == 'GET' and path.endswith('/tracking/live'):
            self._sse()
            return
        rs = ep.get('response_success')
        if isinstance(rs, str):
            # Binary endpoint (photo / dokumen preview).
            self.send_response(200)
            self._cors()
            ctype = ('image/png' if 'photo' in path
                     else 'application/pdf')
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(PNG_1X1)))
            self.end_headers()
            self.wfile.write(PNG_1X1)
            return
        if self.command == 'POST':
            length = int(self.headers.get('Content-Length') or 0)
            if length:
                self.rfile.read(length)
        self._send_json(200, rs)

    def _sse(self):
        payload = ('data: {"employee_id": 15, "latitude": -6.2, '
                   '"longitude": 106.8, "accuracy_m": 12, '
                   '"battery_level": 80, "mock_detected": false, '
                   '"create_date": "2026-11-05 02:00:00"}\n\n').encode()
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8072
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Mock server Ali Attendance API jalan di http://localhost:{port}')
    print(f'Melayani {len(MOCKS)} endpoint mock (POST /ag_rest_api/v1/...).')
    print('Login mock: POST /ag_rest_api/v1/auth/token '
          '(db/login/password bebas) -> token demo-token-mock-server')
    server.serve_forever()


if __name__ == '__main__':
    main()
