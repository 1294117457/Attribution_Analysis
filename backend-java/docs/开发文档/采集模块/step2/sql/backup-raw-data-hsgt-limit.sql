--
-- PostgreSQL database dump
--

\restrict 1H8p3OI0RwPK6zwZOjr2A2f08XD8RwXznnVdDtpJQ1xKB7kUDh46cOwJARyL3Op

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
-- Name: capital_hsgt_top10; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_hsgt_top10 (
    id integer DEFAULT nextval('public.capital_hsgt_top10_id_seq'::regclass) NOT NULL,
    trade_date date NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(50),
    market_type character varying(8) NOT NULL,
    rank integer NOT NULL,
    close double precision,
    p_change double precision,
    amount double precision,
    net_amount double precision,
    buy double precision,
    sell double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    holding_days integer,
    share_ratio double precision,
    hold_amount double precision
);


ALTER TABLE public.capital_hsgt_top10 OWNER TO zhouch;

--
-- Name: capital_limit_list_d; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_limit_list_d (
    id integer DEFAULT nextval('public.capital_limit_list_d_id_seq'::regclass) NOT NULL,
    trade_date date NOT NULL,
    symbol character varying(10) NOT NULL,
    industry character varying(64),
    name character varying(50),
    close double precision,
    pct_chg double precision,
    amount double precision,
    limit_amount double precision,
    float_mv double precision,
    total_mv double precision,
    turnover_ratio double precision,
    fd_amount double precision,
    first_time character varying(8),
    last_time character varying(8),
    open_times integer,
    up_stat character varying(16),
    limit_times integer,
    limit_type character varying(8) NOT NULL,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    close_price double precision,
    change_rate double precision,
    board_count integer,
    first_limit_time time without time zone,
    board_strength double precision,
    reason text
);


ALTER TABLE public.capital_limit_list_d OWNER TO zhouch;

--
-- Name: capital_moneyflow_hsgt; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_moneyflow_hsgt (
    id integer DEFAULT nextval('public.capital_moneyflow_hsgt_id_seq'::regclass) NOT NULL,
    trade_date date NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(50),
    market_type character varying(8) NOT NULL,
    close double precision,
    p_change double precision,
    pct_change double precision,
    rank integer,
    amount double precision,
    net_amount double precision,
    buy double precision,
    sell double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    exchange character varying(8),
    buy_amount double precision,
    sell_amount double precision
);


ALTER TABLE public.capital_moneyflow_hsgt OWNER TO zhouch;

--
-- Data for Name: capital_hsgt_top10; Type: TABLE DATA; Schema: public; Owner: zhouch
--

COPY public.capital_hsgt_top10 (id, trade_date, symbol, name, market_type, rank, close, p_change, amount, net_amount, buy, sell, data_source, created_at, updated_at, holding_days, share_ratio, hold_amount) FROM stdin;
\.


--
-- Data for Name: capital_limit_list_d; Type: TABLE DATA; Schema: public; Owner: zhouch
--

COPY public.capital_limit_list_d (id, trade_date, symbol, industry, name, close, pct_chg, amount, limit_amount, float_mv, total_mv, turnover_ratio, fd_amount, first_time, last_time, open_times, up_stat, limit_times, limit_type, data_source, created_at, updated_at, close_price, change_rate, board_count, first_limit_time, board_strength, reason) FROM stdin;
\.


--
-- Data for Name: capital_moneyflow_hsgt; Type: TABLE DATA; Schema: public; Owner: zhouch
--

COPY public.capital_moneyflow_hsgt (id, trade_date, symbol, name, market_type, close, p_change, pct_change, rank, amount, net_amount, buy, sell, data_source, created_at, updated_at, exchange, buy_amount, sell_amount) FROM stdin;
\.


--
-- Name: capital_hsgt_top10 capital_hsgt_top10_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_hsgt_top10
    ADD CONSTRAINT capital_hsgt_top10_pkey PRIMARY KEY (id);


--
-- Name: capital_limit_list_d capital_limit_list_d_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_limit_list_d
    ADD CONSTRAINT capital_limit_list_d_pkey PRIMARY KEY (id);


--
-- Name: capital_moneyflow_hsgt capital_moneyflow_hsgt_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_moneyflow_hsgt
    ADD CONSTRAINT capital_moneyflow_hsgt_pkey PRIMARY KEY (id);


--
-- Name: capital_hsgt_top10 uq_capital_hsgt_top10_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_hsgt_top10
    ADD CONSTRAINT uq_capital_hsgt_top10_uk UNIQUE (trade_date, market_type, symbol, rank);


--
-- Name: capital_limit_list_d uq_capital_limit_list_d_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_limit_list_d
    ADD CONSTRAINT uq_capital_limit_list_d_uk UNIQUE (trade_date, symbol, limit_type);


--
-- Name: capital_moneyflow_hsgt uq_capital_moneyflow_hsgt_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_moneyflow_hsgt
    ADD CONSTRAINT uq_capital_moneyflow_hsgt_uk UNIQUE (trade_date, symbol, market_type);


--
-- Name: ix_capital_hsgt_top10_market_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_hsgt_top10_market_date ON public.capital_hsgt_top10 USING btree (market_type, trade_date);


--
-- Name: ix_capital_hsgt_top10_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_hsgt_top10_symbol ON public.capital_hsgt_top10 USING btree (symbol);


--
-- Name: ix_capital_hsgt_top10_trade_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_hsgt_top10_trade_date ON public.capital_hsgt_top10 USING btree (trade_date);


--
-- Name: ix_capital_limit_list_d_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_limit_list_d_symbol ON public.capital_limit_list_d USING btree (symbol);


--
-- Name: ix_capital_limit_list_d_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_limit_list_d_symbol_date ON public.capital_limit_list_d USING btree (symbol, trade_date);


--
-- Name: ix_capital_limit_list_d_trade_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_limit_list_d_trade_date ON public.capital_limit_list_d USING btree (trade_date);


--
-- Name: ix_capital_limit_list_d_type_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_limit_list_d_type_date ON public.capital_limit_list_d USING btree (limit_type, trade_date);


--
-- Name: ix_capital_moneyflow_hsgt_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_moneyflow_hsgt_symbol ON public.capital_moneyflow_hsgt USING btree (symbol);


--
-- Name: ix_capital_moneyflow_hsgt_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_moneyflow_hsgt_symbol_date ON public.capital_moneyflow_hsgt USING btree (symbol, trade_date);


--
-- Name: ix_capital_moneyflow_hsgt_trade_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_moneyflow_hsgt_trade_date ON public.capital_moneyflow_hsgt USING btree (trade_date);


--
-- PostgreSQL database dump complete
--

\unrestrict 1H8p3OI0RwPK6zwZOjr2A2f08XD8RwXznnVdDtpJQ1xKB7kUDh46cOwJARyL3Op

