--
-- PostgreSQL database dump
--

\restrict zTLFYkVwa5ryTcEnoTRfOyTobg7QhpbutyvIa3RCId6vkx2KveCEjvnMCXCnERN

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: collect_log; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_log (
    task_id character varying(64) NOT NULL,
    facet character varying(32) NOT NULL,
    name character varying(64) NOT NULL,
    kind character varying(32) NOT NULL,
    mode character varying(16) NOT NULL,
    params_json jsonb,
    range_start date,
    range_end date,
    status character varying(16) NOT NULL,
    total integer NOT NULL,
    done integer NOT NULL,
    success integer NOT NULL,
    fail integer NOT NULL,
    saved_total bigint NOT NULL,
    message text,
    started_at timestamp without time zone,
    finished_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.collect_log OWNER TO zhouch;

--
-- Name: collect_logs; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_logs (
    id uuid NOT NULL,
    service_name character varying(128) NOT NULL,
    category character varying(64) NOT NULL,
    action character varying(32) NOT NULL,
    trigger_source character varying(32) NOT NULL,
    trigger_user character varying(64),
    meta jsonb NOT NULL,
    status character varying(32) NOT NULL,
    total_count integer NOT NULL,
    saved_count integer NOT NULL,
    fail_count integer NOT NULL,
    progress integer NOT NULL,
    error_message text,
    started_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    duration_ms integer
);


ALTER TABLE public.collect_logs OWNER TO zhouch;

--
-- Data for Name: collect_log; Type: TABLE DATA; Schema: public; Owner: zhouch
--

COPY public.collect_log (task_id, facet, name, kind, mode, params_json, range_start, range_end, status, total, done, success, fail, saved_total, message, started_at, finished_at, created_at, updated_at) FROM stdin;
ffc5e26b996047ba	fundamental	stock_basic		condition	{"concurrency": 5, "list_status": "L"}	\N	\N	queued	1	0	0	0	0	排队中	\N	\N	2026-10-29 18:01:20.969836	2026-10-29 18:01:20.969836
\.


--
-- Data for Name: collect_logs; Type: TABLE DATA; Schema: public; Owner: zhouch
--

COPY public.collect_logs (id, service_name, category, action, trigger_source, trigger_user, meta, status, total_count, saved_count, fail_count, progress, error_message, started_at, finished_at, created_at, updated_at, duration_ms) FROM stdin;
d3a30c11-996b-423c-90d1-fa114c9e573d	daily_kline	tech	incremental	manual	\N	{"mode": "condition", "concurrency": 5}	failed	0	0	0	100	Unconsumed column names: trade_date	2026-10-19 15:41:36.234788+08	2026-10-19 15:41:39.467889+08	2026-10-19 15:41:36.9351+08	2026-10-19 15:41:36.9351+08	\N
cbf226c6-207d-4351-ba31-b3d2ce5c9af4	daily_kline	tech	incremental	manual	\N	{"mode": "condition", "concurrency": 5}	failed	0	0	0	100	Column('name', String(length=50), table=<tech_kline_daily>)	2026-10-19 15:43:20.327831+08	2026-10-19 15:44:23.463087+08	2026-10-19 15:43:21.066565+08	2026-10-19 15:43:21.066565+08	\N
8857e10e-b25f-42a9-9f18-93ef2da378a9	daily_kline	tech	incremental	manual	\N	{"mode": "condition", "concurrency": 5}	failed	0	0	0	100	Column('name', String(length=50), table=<tech_kline_daily>)	2026-10-19 15:46:49.024979+08	2026-10-19 15:47:52.185059+08	2026-10-19 15:46:49.858363+08	2026-10-19 15:46:49.858363+08	\N
faf9d484-f53d-47c7-9343-3414dcfedf3d	daily_kline	tech	incremental	manual	\N	{"mode": "condition", "concurrency": 5}	failed	0	0	0	100	Column('name', String(length=50), table=<tech_kline_daily>)	2026-10-19 16:00:54.360115+08	2026-10-19 16:00:57.525594+08	2026-10-19 16:00:55.206567+08	2026-10-19 16:00:55.206567+08	\N
61fa7ab0-a2e3-4d27-b92b-c9875daa8e67	daily_kline	tech	incremental	manual	\N	{"mode": "condition", "concurrency": 5}	failed	0	0	0	100	Column('name', String(length=50), table=<tech_kline_daily>)	2026-10-19 16:00:57.20628+08	2026-10-19 16:01:00.361341+08	2026-10-19 16:00:58.025764+08	2026-10-19 16:00:58.025764+08	\N
9d571fe7-e353-4c55-923c-c9d20f2c29d3	daily_kline	tech	incremental	manual	\N	{"end_date": "2026-11-27", "start_date": "2026-10-11"}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-21T09:16:38.656894	2026-10-20 15:41:36.613906+08	2026-10-21 09:16:38.656915+08	2026-10-20 15:41:36.278198+08	2026-10-20 15:41:36.278198+08	\N
764eb98a-2092-4216-8050-960578172bec	daily_kline	tech	incremental	manual	\N	{"end_date": "2026-11-27", "start_date": "2026-10-11"}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-21T09:16:38.733629	2026-10-20 15:42:39.989528+08	2026-10-21 09:16:38.733639+08	2026-10-20 15:42:39.378541+08	2026-10-20 15:42:39.378541+08	\N
ddc59ef2-005f-4618-a62a-8eaa68896336	daily_kline	tech	incremental	manual	\N	{"mode": "condition", "concurrency": 5}	failed	0	0	0	100	Column('name', String(length=50), table=<tech_kline_daily>)	2026-10-19 16:01:17.992137+08	2026-10-19 16:01:21.231923+08	2026-10-19 16:01:18.680203+08	2026-10-19 16:01:18.680203+08	\N
5c8e9b38-6d7f-490b-b48d-43a7eca30380	dividend	fundamental	incremental	manual	\N	{}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-21T09:16:39.025071	2026-10-20 15:45:05.614183+08	2026-10-21 09:16:39.025076+08	2026-10-20 15:45:05.425037+08	2026-10-20 15:45:05.425037+08	\N
fd393d4b-f27e-4ad4-a6ae-48a1cf8aa13e	daily_kline	tech	incremental	manual	\N	{}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-21T09:16:39.329100	2026-10-20 15:39:52.387248+08	2026-10-21 09:16:39.329106+08	2026-10-20 15:39:52.06924+08	2026-10-20 15:39:52.06924+08	\N
86712574-a32b-40cd-8eb7-bd6a2a3efad9	stock_basic	fundamental	full_refresh	manual	\N	{"concurrency": 5}	failed	0	0	1	100	\N	2026-10-19 16:31:27.765676+08	2026-10-19 16:31:33.513301+08	2026-10-19 16:31:28.614552+08	2026-10-19 16:31:28.614552+08	\N
4b324b3f-5b94-4d1d-af65-aaaeae67b635	stock_basic	fundamental	full_refresh	manual	\N	{"concurrency": 5}	failed	0	0	1	100	\N	2026-10-19 16:32:21.698399+08	2026-10-19 16:32:25.065042+08	2026-10-19 16:32:22.508194+08	2026-10-19 16:32:22.508194+08	\N
ffb4cd0c-7f1e-450c-a691-599fd8edca82	stock_basic	fundamental	full_refresh	manual	\N	{"concurrency": 5}	failed	0	0	1	100	\N	2026-10-19 16:32:39.044143+08	2026-10-19 16:32:43.672909+08	2026-10-19 16:32:39.872696+08	2026-10-19 16:32:39.872696+08	\N
8bfdc6fc-18f9-4f95-b4c4-093734345c0d	stock_basic	fundamental	full_refresh	manual	\N	{"list_status": "L"}	failed	0	0	1	100	\N	2026-10-19 16:35:47.566001+08	2026-10-19 16:35:51.347595+08	2026-10-19 16:35:48.410194+08	2026-10-19 16:35:48.410194+08	\N
1a7b159e-4f2e-45f2-bd6c-3fa432303125	stock_basic	fundamental	full_refresh	manual	\N	{"list_status": "L"}	failed	0	0	1	100	\N	2026-10-19 16:36:29.888304+08	2026-10-19 16:36:32.392888+08	2026-10-19 16:36:30.732848+08	2026-10-19 16:36:30.732848+08	\N
808e81c2-7801-486b-9f83-4473f480c187	stock_basic	fundamental	full_refresh	manual	\N	{"list_status": "L"}	success	0	5575	0	100	\N	2026-10-19 16:37:18.32649+08	2026-10-19 16:37:22.351838+08	2026-10-19 16:37:19.063109+08	2026-10-19 16:37:19.063109+08	\N
c046c5c8-4d20-4ae0-8b7c-07a31f0bbd3b	stock_basic	fundamental	full_refresh	manual	\N	{"list_status": "L"}	success	0	5575	0	100	\N	2026-10-19 16:45:15.618153+08	2026-10-19 16:45:18.440936+08	2026-10-19 16:45:16.474238+08	2026-10-19 16:45:16.474238+08	\N
b119efbc-ceb0-45dc-86c8-45408a02ce35	stock_basic	fundamental	full_refresh	manual	\N	{}	success	0	5575	0	100	\N	2026-10-19 21:25:07.510099+08	2026-10-19 21:25:10.876799+08	2026-10-19 21:25:07.389147+08	2026-10-19 21:25:07.389147+08	\N
a21c4551-5acf-479b-8e1e-180c1b789b96	stock_basic	fundamental	full_refresh	manual	\N	{}	success	0	5575	0	100	\N	2026-10-19 21:26:10.431322+08	2026-10-19 21:26:12.875816+08	2026-10-19 21:26:10.274595+08	2026-10-19 21:26:10.274595+08	\N
4891fbf3-eab6-44de-83f5-a545e43e5a26	stock_basic	fundamental	full_refresh	manual	\N	{}	success	0	5575	0	100	\N	2026-10-19 21:26:20.288476+08	2026-10-19 21:26:22.677456+08	2026-10-19 21:26:20.149349+08	2026-10-19 21:26:20.149349+08	\N
4e90378c-d89d-4dba-a7c6-caf1206e769b	daily_kline	tech	incremental	manual	\N	{"mode": "condition", "concurrency": 5}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-20T12:36:28.796698	2026-10-19 16:02:41.413535+08	2026-10-20 12:36:28.796735+08	2026-10-19 16:02:42.095441+08	2026-10-19 16:02:42.095441+08	\N
51173915-52e0-4846-9e3d-fdb7f4bb2939	daily_kline	tech	incremental	manual	\N	{"mode": "condition", "concurrency": 5}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-20T12:36:28.937344	2026-10-19 16:02:52.997091+08	2026-10-20 12:36:28.937352+08	2026-10-19 16:02:53.870751+08	2026-10-19 16:02:53.870751+08	\N
96c85dcf-3118-46f3-b097-8bb239159f66	stock_basic	fundamental	full_refresh	manual	\N	{"list_status": "L"}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-20T12:36:29.347106	2026-10-19 16:24:39.407577+08	2026-10-20 12:36:29.347112+08	2026-10-19 16:24:40.282782+08	2026-10-19 16:24:40.282782+08	\N
3b5d1aad-70b2-4a91-ba8e-68c8e3f6e392	stock_basic	fundamental	full_refresh	manual	\N	{"list_status": "L"}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-20T12:36:29.778267	2026-10-19 16:24:46.875755+08	2026-10-20 12:36:29.778272+08	2026-10-19 16:24:47.617044+08	2026-10-19 16:24:47.617044+08	\N
e2e2c3a6-73df-44cd-93d0-b97f1bd75c20	daily_kline	tech	incremental	manual	\N	{"end_date": "2026-11-13", "start_date": "2026-10-06"}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-20T12:36:30.188459	2026-10-19 21:27:23.087506+08	2026-10-20 12:36:30.188466+08	2026-10-19 21:27:22.961224+08	2026-10-19 21:27:22.961224+08	\N
536b46ad-d74a-468f-acff-f7b51169d2d6	stock_basic	fundamental	full_refresh	manual	\N	{}	failed	0	0	0	100	StockBasicService.__init__() missing 2 required positional arguments: 'log_service' and 'task_runner'	2026-10-20 12:38:50.09725+08	2026-10-20 12:38:50.595777+08	2026-10-20 12:38:50.87336+08	2026-10-20 12:38:50.87336+08	\N
af3bb7ae-636a-4db0-a273-f5aed4509290	daily_kline	tech	incremental	manual	\N	{}	failed	0	0	0	100	DailyKlineService.__init__() missing 2 required positional arguments: 'log_service' and 'task_runner'	2026-10-20 12:39:15.001879+08	2026-10-20 12:39:15.456251+08	2026-10-20 12:39:15.759465+08	2026-10-20 12:39:15.759465+08	\N
809aa664-429b-4505-a4fa-9acc3cfd856a	stock_basic	fundamental	full_refresh	manual	\N	{}	failed	0	0	0	100	StockBasicService.__init__() missing 2 required positional arguments: 'log_service' and 'task_runner'	2026-10-20 12:39:25.483134+08	2026-10-20 12:39:25.899548+08	2026-10-20 12:39:26.208018+08	2026-10-20 12:39:26.208018+08	\N
d2eaaf53-e0a1-467b-83e4-d7b5cdd7625d	stock_basic	fundamental	full_refresh	manual	\N	{}	success	0	5575	0	100	\N	2026-10-20 12:53:12.836525+08	2026-10-20 12:53:16.046894+08	2026-10-20 12:53:12.628636+08	2026-10-20 12:53:12.628636+08	\N
c4240741-d9e7-41c5-874e-79938f11877d	daily_kline	tech	incremental	manual	\N	{}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-20T14:59:39.500381	2026-10-20 12:53:01.691892+08	2026-10-20 14:59:39.500399+08	2026-10-20 12:53:01.445378+08	2026-10-20 12:53:01.445378+08	\N
3c1e20b1-efa3-40b9-9aec-d33ff248f872	daily_kline	tech	incremental	manual	\N	{"end_date": "2026-11-05", "start_date": "2026-10-09"}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-20T14:59:39.609732	2026-10-20 12:54:32.684651+08	2026-10-20 14:59:39.609741+08	2026-10-20 12:54:32.391494+08	2026-10-20 12:54:32.391494+08	\N
96da12f7-7fc6-4460-8269-718f628ce9de	stock_basic	fundamental	full_refresh	manual	\N	{}	success	0	5575	0	100	\N	2026-10-20 15:39:42.760395+08	2026-10-20 15:39:45.53724+08	2026-10-20 15:39:42.48705+08	2026-10-20 15:39:42.48705+08	\N
7b0947f7-e657-4b85-99a5-13a21060fa3a	name_change	tech	full_refresh	manual	\N	{}	failed	0	0	0	100	(sqlalchemy.dialects.postgresql.asyncpg.InterfaceError) <class 'asyncpg.exceptions._base.InterfaceError'>: the number of query arguments cannot exceed 32767\n[SQL: INSERT INTO tech_name_change (symbol, name, start_date, end_date, ann_date, change_reason, data_source) VALUES ($1::VARCHAR, $2::VARCHAR, $3::DATE, $4::DATE, $5::DATE, $6::VARCHAR, $7::VARCHAR), ($8::VARCHAR, $9::VARCHAR, $10::DATE, $11::DATE, $12::DATE, $13::VARCHAR, $14::VARCHAR), ($15::VARCHAR, $16::VARCHAR, $17::DATE, $18::DATE, $1	2026-10-20 15:44:44.874425+08	2026-10-20 15:44:49.03099+08	2026-10-20 15:44:44.695771+08	2026-10-20 15:44:44.695771+08	\N
31bfae72-bb2d-4013-bb97-734ab86a6e84	daily_basic	fundamental	incremental	manual	\N	{}	success	0	0	0	100	\N	2026-10-20 15:45:14.377866+08	2026-10-20 15:46:14.880709+08	2026-10-20 15:45:14.210863+08	2026-10-20 15:45:14.210863+08	\N
fd08b15f-2690-4133-bdba-6f4eb1cd225d	adj_factor	tech	incremental	manual	\N	{}	failed	0	3879	0	100	tushare.adj_factor: HTTPConnectionPool(host='api.waditu.com', port=80): Max retries exceeded with url: / (Caused by NameResolutionError("<urllib3.connection.HTTPConnection object at 0x7a60ba7f51f0>: Failed to resolve 'api.waditu.com' ([Errno -2] Name or service not known)"))	2026-10-20 15:44:55.785109+08	2026-10-20 16:41:42.177339+08	2026-10-20 15:44:55.599172+08	2026-10-20 15:44:55.599172+08	\N
c8e00e6a-c701-4749-b336-9d6c3d78126c	stock_basic	fundamental	full_refresh	manual	\N	{}	success	0	5576	0	100	\N	2026-10-21 09:17:08.424355+08	2026-10-21 09:17:11.114694+08	2026-10-21 09:17:09.306392+08	2026-10-21 09:17:09.306392+08	\N
8ed3a06d-9362-483c-9e4f-57d0e2593b56	daily_kline	tech	incremental	manual	\N	{}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-21T20:56:05.439886	2026-10-21 09:17:20.560419+08	2026-10-21 20:56:05.439901+08	2026-10-21 09:17:21.094569+08	2026-10-21 09:17:21.094569+08	\N
19cd66bb-b540-472e-901a-9405c155a7ed	daily_kline	tech	incremental	manual	\N	{"end_date": "2026-10-21", "start_date": "2025-10-21"}	failed	0	0	0	100	process_restart: orphan recovered at 2026-10-21T20:56:05.545678	2026-10-21 09:19:33.753844+08	2026-10-21 20:56:05.545695+08	2026-10-21 09:19:34.291474+08	2026-10-21 09:19:34.291474+08	\N
4db1d14c-7f54-4dd4-b3e6-17477a13f07e	stock_basic	fundamental	full_refresh	manual	\N	{}	success	0	5576	0	100	\N	2026-10-21 20:56:37.782936+08	2026-10-21 20:56:44.873442+08	2026-10-21 20:56:44.693807+08	2026-10-21 20:56:44.693807+08	\N
be8ae7ee-45b4-42e0-945e-b0783f256788	daily	tech	incremental	manual	\N	{"end_date": "2024-01-07", "start_date": "2024-01-01"}	failed	0	0	4	100	\N	2026-10-24 09:33:33.036895+08	2026-10-24 09:33:51.377412+08	2026-10-24 09:33:33.479017+08	2026-10-24 09:33:33.479017+08	\N
0dd2cbce-5292-4b51-9318-94bb5aa9ffe2	daily	tech	incremental	manual	\N	{"end_date": "2024-01-07", "start_date": "2024-01-01"}	failed	0	0	4	100	\N	2026-10-24 09:36:48.476798+08	2026-10-24 09:37:05.422158+08	2026-10-24 09:36:48.930918+08	2026-10-24 09:36:48.930918+08	\N
496ae7d8-6663-4d76-b8c3-88a08ad2a652	adj_factor	tech	incremental	manual	\N	{}	failed	0	0	0	0	process_restart: orphan recovered at 2026-10-25T14:58:22.110437	2026-10-24 09:42:18.971796+08	2026-10-25 14:58:22.110452+08	2026-10-24 09:42:19.308138+08	2026-10-24 09:42:19.308138+08	\N
ecd94262-cb30-4a0c-850e-2d8f6c918bd7	daily	tech	incremental	manual	\N	{"end_date": "2026-11-12", "start_date": "2026-10-06"}	failed	38	0	12	100	InterfaceError("(sqlalchemy.dialects.postgresql.asyncpg.InterfaceError) <class 'asyncpg.exceptions._base.InterfaceError'>: the number of query arguments cannot exceed 32767")	2026-10-25 14:58:56.616716+08	2026-10-25 14:59:30.645366+08	2026-10-25 14:58:56.457812+08	2026-10-25 14:58:56.457812+08	\N
b8a10473-dfdf-40c7-9886-b8c9843bf3e7	daily	tech	incremental	manual	\N	{"end_date": "2026-10-09", "start_date": "2026-09-24"}	failed	0	0	6	100	\N	2026-10-25 09:41:47.240071+08	2026-10-25 09:42:04.648181+08	2026-10-25 17:41:46.8875+08	2026-10-25 17:41:46.8875+08	\N
bdf51a4c-57c3-4d5d-9cc7-84d8d0f9ebf5	daily	tech	incremental	manual	\N	{"end_date": "2026-11-25", "start_date": "2026-10-21"}	running	0	0	0	0	\N	2026-10-25 10:15:55.18293+08	\N	2026-10-25 18:15:54.772803+08	2026-10-25 18:15:54.772803+08	\N
46e17199-33e4-4063-85bb-3b60834adbbe	daily	tech	incremental	manual	\N	{"end_date": "2026-10-06", "start_date": "2026-09-17"}	success	0	9	0	100	\N	2026-10-25 10:16:30.285371+08	2026-10-25 10:16:52.650909+08	2026-10-25 18:16:29.936364+08	2026-10-25 18:16:29.936364+08	\N
c694fa89-b389-4721-86ea-21f82950fe3f	daily	tech	incremental	manual	\N	{"end_date": "2026-11-12", "start_date": "2026-10-05"}	failed	0	0	0	0	not enough values to unpack (expected 3, got 2)	2026-10-26 18:34:11.989822+08	2026-10-26 18:34:12.518322+08	2026-10-26 18:34:12.217507+08	2026-10-26 18:34:12.754246+08	\N
1b075b30-3d5c-4498-83a8-48a1e43058c3	daily	tech	incremental	manual	\N	{"end_date": "2026-10-07", "start_date": "2026-09-01"}	failed	0	0	0	0	not enough values to unpack (expected 3, got 2)	2026-10-26 18:34:37.790497+08	2026-10-26 18:34:41.700203+08	2026-10-26 18:34:38.01753+08	2026-10-26 18:34:41.926965+08	\N
fac853d2-2ecf-4946-a811-5a47838f1fe8	daily	tech	incremental	manual	\N	{"end_date": "2026-10-14", "start_date": "2026-09-17"}	failed	0	0	0	0	'LogUtil' object has no attribute 'update_cache'	2026-10-26 18:51:16.053197+08	2026-10-26 18:51:16.348015+08	2026-10-26 18:51:16.29579+08	2026-10-26 18:51:16.593976+08	\N
ca41392c-8ae0-455f-a0b3-f4a80484fdeb	daily	tech	incremental	manual	\N	{"end_date": "2026-10-07", "start_date": "2026-09-10"}	failed	0	0	0	0	not enough values to unpack (expected 3, got 2)	2026-10-27 13:48:12.509192+08	2026-10-27 13:48:15.68156+08	2026-10-27 13:48:12.965127+08	2026-10-27 13:48:16.140284+08	2873
\.


--
-- Name: collect_log collect_log_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_log
    ADD CONSTRAINT collect_log_pkey PRIMARY KEY (task_id);


--
-- Name: collect_logs collect_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_logs
    ADD CONSTRAINT collect_logs_pkey PRIMARY KEY (id);


--
-- Name: idx_collect_logs_service_name; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX idx_collect_logs_service_name ON public.collect_logs USING btree (service_name);


--
-- Name: idx_collect_logs_service_time; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX idx_collect_logs_service_time ON public.collect_logs USING btree (service_name, started_at DESC);


--
-- Name: idx_collect_logs_started_at; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX idx_collect_logs_started_at ON public.collect_logs USING btree (started_at DESC);


--
-- Name: idx_collect_logs_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX idx_collect_logs_status ON public.collect_logs USING btree (status);


--
-- Name: ix_collect_log_created; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_log_created ON public.collect_log USING btree (created_at);


--
-- Name: ix_collect_log_name_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_log_name_status ON public.collect_log USING btree (name, status);


--
-- PostgreSQL database dump complete
--

\unrestrict zTLFYkVwa5ryTcEnoTRfOyTobg7QhpbutyvIa3RCId6vkx2KveCEjvnMCXCnERN

