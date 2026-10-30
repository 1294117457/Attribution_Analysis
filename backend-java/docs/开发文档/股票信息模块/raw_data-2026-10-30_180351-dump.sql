--
-- PostgreSQL database dump
--

\restrict rCjVjD0sDMIRyNbnPVMX1Uwn7vx3R5I8bboZzEaHnsmycIpxa5XN3QFzF1f7ja6

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

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: capital_block_trade_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.capital_block_trade_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_block_trade_id_seq OWNER TO pg_database_owner;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: capital_block_trade; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_block_trade (
    id integer DEFAULT nextval('public.capital_block_trade_id_seq'::regclass) NOT NULL,
    trade_date date NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(50),
    price double precision,
    vol double precision,
    amount double precision,
    buyer character varying(128),
    seller character varying(128),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_block_trade OWNER TO zhouch;

--
-- Name: COLUMN capital_block_trade.price; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_block_trade.price IS '成交价';


--
-- Name: COLUMN capital_block_trade.vol; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_block_trade.vol IS '成交量(万股)';


--
-- Name: COLUMN capital_block_trade.amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_block_trade.amount IS '成交金额';


--
-- Name: COLUMN capital_block_trade.buyer; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_block_trade.buyer IS '买方营业部';


--
-- Name: COLUMN capital_block_trade.seller; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_block_trade.seller IS '卖方营业部';


--
-- Name: capital_hsgt_top10_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.capital_hsgt_top10_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_hsgt_top10_id_seq OWNER TO zhouch;

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
    change double precision,
    amount double precision,
    net_amount double precision,
    buy double precision,
    sell double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_hsgt_top10 OWNER TO zhouch;

--
-- Name: TABLE capital_hsgt_top10; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON TABLE public.capital_hsgt_top10 IS '沪深股通每日十大成交股（Tushare hsgt_top10 官方结构）';


--
-- Name: COLUMN capital_hsgt_top10.market_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_hsgt_top10.market_type IS '市场类型（1=沪市 3=深市）';


--
-- Name: COLUMN capital_hsgt_top10.rank; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_hsgt_top10.rank IS '资金排名（1-10）';


--
-- Name: COLUMN capital_hsgt_top10.change; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_hsgt_top10.change IS '涨跌额';


--
-- Name: COLUMN capital_hsgt_top10.amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_hsgt_top10.amount IS '成交金额（元）';


--
-- Name: COLUMN capital_hsgt_top10.net_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_hsgt_top10.net_amount IS '净成交金额（元）';


--
-- Name: COLUMN capital_hsgt_top10.buy; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_hsgt_top10.buy IS '买入金额（元）';


--
-- Name: COLUMN capital_hsgt_top10.sell; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_hsgt_top10.sell IS '卖出金额（元）';


--
-- Name: capital_limit_list_d_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.capital_limit_list_d_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_limit_list_d_id_seq OWNER TO zhouch;

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
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_limit_list_d OWNER TO zhouch;

--
-- Name: TABLE capital_limit_list_d; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON TABLE public.capital_limit_list_d IS '每日涨跌停板（Tushare limit_list_d 官方结构）';


--
-- Name: COLUMN capital_limit_list_d.limit_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_limit_list_d.limit_amount IS '板上成交金额';


--
-- Name: COLUMN capital_limit_list_d.fd_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_limit_list_d.fd_amount IS '封单金额';


--
-- Name: COLUMN capital_limit_list_d.open_times; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_limit_list_d.open_times IS '炸板次数';


--
-- Name: COLUMN capital_limit_list_d.up_stat; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_limit_list_d.up_stat IS '涨停统计（N/T T天有N次涨停）';


--
-- Name: COLUMN capital_limit_list_d.limit_times; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_limit_list_d.limit_times IS '连板数';


--
-- Name: COLUMN capital_limit_list_d.limit_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_limit_list_d.limit_type IS '涨跌停类型（U涨停 D跌停 Z炸板）';


--
-- Name: capital_margin_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.capital_margin_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_margin_id_seq OWNER TO pg_database_owner;

--
-- Name: capital_margin; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_margin (
    id integer DEFAULT nextval('public.capital_margin_id_seq'::regclass) NOT NULL,
    trade_date date NOT NULL,
    exchange_id character varying(16) NOT NULL,
    rzye double precision,
    rzmre double precision,
    rzche double precision,
    rqye double precision,
    rqmcl double precision,
    rzrqye double precision,
    rqyl double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_margin OWNER TO zhouch;

--
-- Name: COLUMN capital_margin.exchange_id; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin.exchange_id IS '交易所代码 SSE/SZSE';


--
-- Name: COLUMN capital_margin.rzye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin.rzye IS '融资余额(元)';


--
-- Name: COLUMN capital_margin.rzmre; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin.rzmre IS '融资买入额(元)';


--
-- Name: COLUMN capital_margin.rzche; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin.rzche IS '融资偿还额(元)';


--
-- Name: COLUMN capital_margin.rqye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin.rqye IS '融券余额(元)';


--
-- Name: COLUMN capital_margin.rqmcl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin.rqmcl IS '融券卖出量(股)';


--
-- Name: COLUMN capital_margin.rzrqye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin.rzrqye IS '融资融券余额(元)';


--
-- Name: COLUMN capital_margin.rqyl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin.rqyl IS '融券余量(股)';


--
-- Name: capital_margin_detail_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.capital_margin_detail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_margin_detail_id_seq OWNER TO pg_database_owner;

--
-- Name: capital_margin_detail; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_margin_detail (
    id integer DEFAULT nextval('public.capital_margin_detail_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    trade_date date NOT NULL,
    rzye double precision,
    rqye double precision,
    rzmre double precision,
    rqyl double precision,
    rzche double precision,
    rqchl double precision,
    rqmcl double precision,
    rzrqye double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    name character varying(50)
);


ALTER TABLE public.capital_margin_detail OWNER TO zhouch;

--
-- Name: COLUMN capital_margin_detail.rzye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin_detail.rzye IS '融资余额';


--
-- Name: COLUMN capital_margin_detail.rqye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin_detail.rqye IS '融券余额';


--
-- Name: COLUMN capital_margin_detail.rzmre; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin_detail.rzmre IS '融资买入额';


--
-- Name: COLUMN capital_margin_detail.rqyl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin_detail.rqyl IS '融券余量';


--
-- Name: COLUMN capital_margin_detail.rzche; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin_detail.rzche IS '融资偿还额';


--
-- Name: COLUMN capital_margin_detail.rqchl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin_detail.rqchl IS '融券偿还量';


--
-- Name: COLUMN capital_margin_detail.rqmcl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin_detail.rqmcl IS '融券卖出量';


--
-- Name: COLUMN capital_margin_detail.rzrqye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_margin_detail.rzrqye IS '融资融券余额';


--
-- Name: capital_moneyflow_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.capital_moneyflow_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_moneyflow_id_seq OWNER TO pg_database_owner;

--
-- Name: capital_moneyflow; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_moneyflow (
    id integer DEFAULT nextval('public.capital_moneyflow_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    trade_date date NOT NULL,
    buy_sm_vol double precision,
    buy_sm_amount double precision,
    sell_sm_vol double precision,
    sell_sm_amount double precision,
    buy_md_vol double precision,
    buy_md_amount double precision,
    sell_md_vol double precision,
    sell_md_amount double precision,
    buy_lg_vol double precision,
    buy_lg_amount double precision,
    sell_lg_vol double precision,
    sell_lg_amount double precision,
    buy_elg_vol double precision,
    buy_elg_amount double precision,
    sell_elg_vol double precision,
    sell_elg_amount double precision,
    net_mf_vol double precision,
    net_mf_amount double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_moneyflow OWNER TO zhouch;

--
-- Name: capital_moneyflow_hsgt; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_moneyflow_hsgt (
    id integer NOT NULL,
    trade_date date NOT NULL,
    ggt_ss double precision,
    ggt_sz double precision,
    hgt double precision,
    sgt double precision,
    north_money double precision,
    south_money double precision,
    data_source character varying(16) DEFAULT 'tushare'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_moneyflow_hsgt OWNER TO zhouch;

--
-- Name: TABLE capital_moneyflow_hsgt; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON TABLE public.capital_moneyflow_hsgt IS '沪深港通资金流向（Tushare moneyflow_hsgt 官方结构：一行=一个交易日的资金流汇总）';


--
-- Name: COLUMN capital_moneyflow_hsgt.ggt_ss; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_moneyflow_hsgt.ggt_ss IS '港股通（上海）成交金额（百万元）';


--
-- Name: COLUMN capital_moneyflow_hsgt.ggt_sz; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_moneyflow_hsgt.ggt_sz IS '港股通（深圳）成交金额（百万元）';


--
-- Name: COLUMN capital_moneyflow_hsgt.north_money; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_moneyflow_hsgt.north_money IS '北向资金（百万元）';


--
-- Name: COLUMN capital_moneyflow_hsgt.south_money; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_moneyflow_hsgt.south_money IS '南向资金（百万元）';


--
-- Name: capital_moneyflow_hsgt_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.capital_moneyflow_hsgt_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_moneyflow_hsgt_id_seq OWNER TO zhouch;

--
-- Name: capital_moneyflow_hsgt_id_seq1; Type: SEQUENCE; Schema: public; Owner: zhouch
--

ALTER TABLE public.capital_moneyflow_hsgt ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.capital_moneyflow_hsgt_id_seq1
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: capital_stk_holdernumber_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.capital_stk_holdernumber_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_stk_holdernumber_id_seq OWNER TO pg_database_owner;

--
-- Name: capital_stk_holdernumber; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_stk_holdernumber (
    id integer DEFAULT nextval('public.capital_stk_holdernumber_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    ann_date date,
    end_date date NOT NULL,
    holder_num integer,
    holder_nums double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_stk_holdernumber OWNER TO zhouch;

--
-- Name: COLUMN capital_stk_holdernumber.holder_num; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_stk_holdernumber.holder_num IS '股东户数';


--
-- Name: COLUMN capital_stk_holdernumber.holder_nums; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_stk_holdernumber.holder_nums IS '股东户数(详细)';


--
-- Name: capital_top_inst_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.capital_top_inst_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_top_inst_id_seq OWNER TO pg_database_owner;

--
-- Name: capital_top_inst; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_top_inst (
    id integer DEFAULT nextval('public.capital_top_inst_id_seq'::regclass) NOT NULL,
    trade_date date NOT NULL,
    symbol character varying(10) NOT NULL,
    exalter character varying(128),
    side character varying(8),
    buy double precision,
    buy_rate double precision,
    sell double precision,
    sell_rate double precision,
    net_buy double precision,
    reason character varying(256),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_top_inst OWNER TO zhouch;

--
-- Name: COLUMN capital_top_inst.exalter; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_inst.exalter IS '营业部名称';


--
-- Name: COLUMN capital_top_inst.side; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_inst.side IS '买卖方向: 0=卖/1=买';


--
-- Name: COLUMN capital_top_inst.buy; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_inst.buy IS '买入额';


--
-- Name: COLUMN capital_top_inst.buy_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_inst.buy_rate IS '买入占总成交比';


--
-- Name: COLUMN capital_top_inst.sell; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_inst.sell IS '卖出额';


--
-- Name: COLUMN capital_top_inst.sell_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_inst.sell_rate IS '卖出占总成交比';


--
-- Name: COLUMN capital_top_inst.net_buy; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_inst.net_buy IS '净额';


--
-- Name: COLUMN capital_top_inst.reason; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_inst.reason IS '上榜原因';


--
-- Name: capital_top_list_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.capital_top_list_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.capital_top_list_id_seq OWNER TO pg_database_owner;

--
-- Name: capital_top_list; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.capital_top_list (
    id integer DEFAULT nextval('public.capital_top_list_id_seq'::regclass) NOT NULL,
    trade_date date NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(50),
    close double precision,
    pct_change double precision,
    turnover_rate double precision,
    amount double precision,
    l_sell double precision,
    l_buy double precision,
    l_amount double precision,
    net_amount double precision,
    net_rate double precision,
    amount_rate double precision,
    float_values double precision,
    reason character varying(256),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.capital_top_list OWNER TO zhouch;

--
-- Name: COLUMN capital_top_list.l_sell; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_list.l_sell IS '龙虎榜卖出额';


--
-- Name: COLUMN capital_top_list.l_buy; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_list.l_buy IS '龙虎榜买入额';


--
-- Name: COLUMN capital_top_list.l_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_list.l_amount IS '龙虎榜成交额';


--
-- Name: COLUMN capital_top_list.net_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_list.net_amount IS '净买入额';


--
-- Name: COLUMN capital_top_list.net_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_list.net_rate IS '净买/总成交';


--
-- Name: COLUMN capital_top_list.amount_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_list.amount_rate IS '成交额占比';


--
-- Name: COLUMN capital_top_list.float_values; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_list.float_values IS '流通市值';


--
-- Name: COLUMN capital_top_list.reason; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.capital_top_list.reason IS '上榜原因';


--
-- Name: fundamental_concept_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_concept_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_concept_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_concept; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_concept (
    id integer DEFAULT nextval('public.fundamental_concept_id_seq'::regclass) NOT NULL,
    index_code character varying(10) NOT NULL,
    concept_code character varying(10),
    name character varying(100) NOT NULL,
    source character varying(10) DEFAULT 'ths'::character varying NOT NULL,
    concept_type character varying(50) DEFAULT 'other'::character varying NOT NULL,
    description text,
    stock_count integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    first_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    last_synced_at timestamp with time zone
);


ALTER TABLE public.fundamental_concept OWNER TO zhouch;

--
-- Name: fundamental_concept_index_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_concept_index_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_concept_index_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_concept_index; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_concept_index (
    id integer DEFAULT nextval('public.fundamental_concept_index_id_seq'::regclass) NOT NULL,
    index_code character varying(10) NOT NULL,
    concept_name character varying(100) NOT NULL,
    trade_date date NOT NULL,
    open double precision DEFAULT 0.0 NOT NULL,
    high double precision DEFAULT 0.0 NOT NULL,
    low double precision DEFAULT 0.0 NOT NULL,
    close double precision DEFAULT 0.0 NOT NULL,
    volume bigint DEFAULT 0 NOT NULL,
    amount double precision DEFAULT 0.0 NOT NULL,
    change double precision,
    change_pct double precision,
    captured_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fundamental_concept_index OWNER TO zhouch;

--
-- Name: fundamental_concept_member; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_concept_member (
    symbol character varying(10) NOT NULL,
    concept_id integer NOT NULL,
    reason text,
    joined_at timestamp with time zone DEFAULT now() NOT NULL,
    synced_at timestamp with time zone DEFAULT now() NOT NULL,
    source character varying(10) DEFAULT 'ths'::character varying NOT NULL,
    short_name character varying(50)
);


ALTER TABLE public.fundamental_concept_member OWNER TO zhouch;

--
-- Name: fundamental_concept_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_concept_snapshot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_concept_snapshot_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_concept_snapshot; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_concept_snapshot (
    id integer DEFAULT nextval('public.fundamental_concept_snapshot_id_seq'::regclass) NOT NULL,
    index_code character varying(10) NOT NULL,
    concept_name character varying(100) NOT NULL,
    trade_time timestamp without time zone,
    open_price double precision,
    high double precision,
    low double precision,
    price double precision,
    prev_close double precision,
    p_change double precision,
    rank_current integer,
    rank_total integer,
    up_count integer,
    down_count integer,
    volume_wan double precision,
    turnover_yi double precision,
    net_inflow_yi double precision,
    source character varying(10) DEFAULT 'ths'::character varying NOT NULL,
    captured_at timestamp with time zone DEFAULT now() NOT NULL,
    trade_date date,
    pct_change double precision
);


ALTER TABLE public.fundamental_concept_snapshot OWNER TO zhouch;

--
-- Name: fundamental_daily_basic_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_daily_basic_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_daily_basic_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_daily_basic; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_daily_basic (
    id integer DEFAULT nextval('public.fundamental_daily_basic_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    trade_date date NOT NULL,
    close double precision,
    turnover_rate double precision,
    turnover_rate_f double precision,
    volume_ratio double precision,
    pe double precision,
    pe_ttm double precision,
    pb double precision,
    ps double precision,
    ps_ttm double precision,
    dv_ratio double precision,
    dv_ttm double precision,
    total_share double precision,
    float_share double precision,
    free_share double precision,
    total_mv double precision,
    circ_mv double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    limit_status integer
);


ALTER TABLE public.fundamental_daily_basic OWNER TO zhouch;

--
-- Name: COLUMN fundamental_daily_basic.turnover_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.turnover_rate IS '换手率%';


--
-- Name: COLUMN fundamental_daily_basic.turnover_rate_f; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.turnover_rate_f IS '换手率(自由流通)';


--
-- Name: COLUMN fundamental_daily_basic.volume_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.volume_ratio IS '量比';


--
-- Name: COLUMN fundamental_daily_basic.pe; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.pe IS '市盈率(动)';


--
-- Name: COLUMN fundamental_daily_basic.pe_ttm; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.pe_ttm IS '市盈率TTM';


--
-- Name: COLUMN fundamental_daily_basic.pb; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.pb IS '市净率';


--
-- Name: COLUMN fundamental_daily_basic.ps; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.ps IS '市销率';


--
-- Name: COLUMN fundamental_daily_basic.ps_ttm; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.ps_ttm IS '市销率TTM';


--
-- Name: COLUMN fundamental_daily_basic.dv_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.dv_ratio IS '股息率%';


--
-- Name: COLUMN fundamental_daily_basic.dv_ttm; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.dv_ttm IS '股息率TTM%';


--
-- Name: COLUMN fundamental_daily_basic.total_share; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.total_share IS '总股本(万股)';


--
-- Name: COLUMN fundamental_daily_basic.float_share; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.float_share IS '流通股本(万股)';


--
-- Name: COLUMN fundamental_daily_basic.free_share; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.free_share IS '自由流通股本(万股)';


--
-- Name: COLUMN fundamental_daily_basic.total_mv; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.total_mv IS '总市值(万元)';


--
-- Name: COLUMN fundamental_daily_basic.circ_mv; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_daily_basic.circ_mv IS '流通市值(万元)';


--
-- Name: fundamental_dividend_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_dividend_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_dividend_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_dividend; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_dividend (
    id integer DEFAULT nextval('public.fundamental_dividend_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    end_date date NOT NULL,
    ann_date date,
    record_date date,
    ex_date date,
    pay_date date,
    div_proc character varying(16),
    stk_div double precision,
    stk_bo_rate double precision,
    stk_co_rate double precision,
    cash_div double precision,
    cash_div_tax double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    div_listdate date,
    imp_ann_date date
);


ALTER TABLE public.fundamental_dividend OWNER TO zhouch;

--
-- Name: COLUMN fundamental_dividend.div_proc; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_dividend.div_proc IS '实施进度';


--
-- Name: COLUMN fundamental_dividend.stk_div; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_dividend.stk_div IS '每股送股';


--
-- Name: COLUMN fundamental_dividend.stk_bo_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_dividend.stk_bo_rate IS '每股转增比例';


--
-- Name: COLUMN fundamental_dividend.stk_co_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_dividend.stk_co_rate IS '每股送股比例';


--
-- Name: COLUMN fundamental_dividend.cash_div; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_dividend.cash_div IS '每股派息(税前)';


--
-- Name: COLUMN fundamental_dividend.cash_div_tax; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_dividend.cash_div_tax IS '每股派息(税后)';


--
-- Name: fundamental_income_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_income_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_income_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_income; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_income (
    id integer DEFAULT nextval('public.fundamental_income_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    ann_date date,
    end_date date NOT NULL,
    report_type character varying(16),
    comp_type character varying(16),
    basic_eps double precision,
    diluted_eps double precision,
    total_revenue double precision,
    revenue double precision,
    operate_profit double precision,
    total_profit double precision,
    n_income double precision,
    n_income_attr_p double precision,
    total_assets double precision,
    total_liab double precision,
    total_hldr_eqy_exc_min_int double precision,
    n_cashflow_act double precision,
    n_cash_flows_fnc_act double precision,
    n_cashflow_inv_act double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    end_type character varying(8)
);


ALTER TABLE public.fundamental_income OWNER TO zhouch;

--
-- Name: COLUMN fundamental_income.report_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.report_type IS '报表类型(Tushare): 1=合并报表 2=单季合并 6=母公司报表…，本项目只采 1';


--
-- Name: COLUMN fundamental_income.comp_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.comp_type IS '公司类型: 1=一般工商业 2=银行 3=保险 4=证券 7=多元金融';


--
-- Name: COLUMN fundamental_income.basic_eps; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.basic_eps IS '基本每股收益';


--
-- Name: COLUMN fundamental_income.diluted_eps; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.diluted_eps IS '稀释每股收益';


--
-- Name: COLUMN fundamental_income.total_revenue; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.total_revenue IS '营业总收入';


--
-- Name: COLUMN fundamental_income.revenue; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.revenue IS '营业收入';


--
-- Name: COLUMN fundamental_income.operate_profit; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.operate_profit IS '营业利润';


--
-- Name: COLUMN fundamental_income.total_profit; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.total_profit IS '利润总额';


--
-- Name: COLUMN fundamental_income.n_income; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.n_income IS '净利润';


--
-- Name: COLUMN fundamental_income.n_income_attr_p; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.n_income_attr_p IS '归属母公司股东的净利润';


--
-- Name: COLUMN fundamental_income.total_assets; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.total_assets IS '资产总计';


--
-- Name: COLUMN fundamental_income.total_liab; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.total_liab IS '负债合计';


--
-- Name: COLUMN fundamental_income.total_hldr_eqy_exc_min_int; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.total_hldr_eqy_exc_min_int IS '归属母公司股东权益';


--
-- Name: COLUMN fundamental_income.n_cashflow_act; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.n_cashflow_act IS '经营活动现金流量净额';


--
-- Name: COLUMN fundamental_income.n_cash_flows_fnc_act; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.n_cash_flows_fnc_act IS '筹资活动现金流量净额';


--
-- Name: COLUMN fundamental_income.n_cashflow_inv_act; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_income.n_cashflow_inv_act IS '投资活动现金流量净额';


--
-- Name: fundamental_index_daily_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_index_daily_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_index_daily_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_index_daily; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_index_daily (
    id integer DEFAULT nextval('public.fundamental_index_daily_id_seq'::regclass) NOT NULL,
    market character varying(16) NOT NULL,
    trade_date date NOT NULL,
    close double precision,
    open double precision,
    high double precision,
    low double precision,
    pre_close double precision,
    change double precision,
    pct_chg double precision,
    vol double precision,
    amount double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fundamental_index_daily OWNER TO zhouch;

--
-- Name: COLUMN fundamental_index_daily.market; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_index_daily.market IS '市场代码: SSE/SZSE/CSI';


--
-- Name: fundamental_index_member_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_index_member_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_index_member_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_index_member; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_index_member (
    id integer DEFAULT nextval('public.fundamental_index_member_id_seq'::regclass) NOT NULL,
    sector_type character varying(16) NOT NULL,
    sector_code character varying(32) NOT NULL,
    sector_name character varying(64),
    symbol character varying(10) NOT NULL,
    name character varying(50),
    effective_date date,
    expiry_date date,
    is_new character varying(8),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fundamental_index_member OWNER TO zhouch;

--
-- Name: COLUMN fundamental_index_member.sector_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_index_member.sector_type IS '板块类型: industry/concept/area';


--
-- Name: COLUMN fundamental_index_member.sector_code; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_index_member.sector_code IS '板块代码';


--
-- Name: COLUMN fundamental_index_member.effective_date; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_index_member.effective_date IS '纳入日期';


--
-- Name: COLUMN fundamental_index_member.expiry_date; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_index_member.expiry_date IS '剔除日期';


--
-- Name: COLUMN fundamental_index_member.is_new; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_index_member.is_new IS 'Y/N';


--
-- Name: fundamental_market_daily; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_market_daily (
    id integer NOT NULL,
    market character varying(16) NOT NULL,
    trade_date date NOT NULL,
    close double precision,
    open double precision,
    high double precision,
    low double precision,
    pre_close double precision,
    change double precision,
    pct_chg double precision,
    vol double precision,
    amount double precision,
    data_source character varying(16) DEFAULT 'tushare'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fundamental_market_daily OWNER TO zhouch;

--
-- Name: TABLE fundamental_market_daily; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON TABLE public.fundamental_market_daily IS '市场大盘日线（market= SSE/SZSE/CSI）';


--
-- Name: COLUMN fundamental_market_daily.market; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_market_daily.market IS '市场代码: SSE/SZSE/CSI';


--
-- Name: fundamental_market_daily_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

ALTER TABLE public.fundamental_market_daily ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.fundamental_market_daily_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: fundamental_sector_daily_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_sector_daily_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_sector_daily_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_sector_daily; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_sector_daily (
    id integer DEFAULT nextval('public.fundamental_sector_daily_id_seq'::regclass) NOT NULL,
    sector_type character varying(16) NOT NULL,
    sector_code character varying(32) NOT NULL,
    sector_name character varying(64),
    trade_date date NOT NULL,
    close double precision,
    open double precision,
    high double precision,
    low double precision,
    pre_close double precision,
    change double precision,
    pct_change double precision,
    vol double precision,
    amount double precision,
    turnover_rate double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fundamental_sector_daily OWNER TO zhouch;

--
-- Name: COLUMN fundamental_sector_daily.sector_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_sector_daily.sector_type IS '板块类型: industry/concept/area';


--
-- Name: COLUMN fundamental_sector_daily.sector_code; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_sector_daily.sector_code IS '板块代码';


--
-- Name: COLUMN fundamental_sector_daily.sector_name; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_sector_daily.sector_name IS '板块名称';


--
-- Name: fundamental_stock_basic_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_stock_basic_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_stock_basic_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_stock_basic; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_stock_basic (
    id integer DEFAULT nextval('public.fundamental_stock_basic_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    ts_code character varying(20),
    name character varying(100),
    area character varying(50),
    industry character varying(100),
    market character varying(50),
    exchange character varying(10),
    list_date date,
    delist_date date,
    list_status character varying(5) DEFAULT 'L'::character varying,
    is_hs character varying(5) DEFAULT 'N'::character varying,
    act_name character varying(200),
    act_ent_type character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    fullname character varying(200),
    enname character varying(200),
    cnspell character varying(20),
    curr_type character varying(8),
    total_shares bigint
);


ALTER TABLE public.fundamental_stock_basic OWNER TO zhouch;

--
-- Name: COLUMN fundamental_stock_basic.symbol; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.symbol IS '股票代码（6位）';


--
-- Name: COLUMN fundamental_stock_basic.ts_code; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.ts_code IS 'Tushare 统一代码（含交易所后缀）';


--
-- Name: COLUMN fundamental_stock_basic.area; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.area IS '地域';


--
-- Name: COLUMN fundamental_stock_basic.industry; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.industry IS '行业';


--
-- Name: COLUMN fundamental_stock_basic.market; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.market IS '市场类型（主板/科创板/创业板/北交所）';


--
-- Name: COLUMN fundamental_stock_basic.exchange; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.exchange IS '交易所代码 SSE/SZSE/BSE';


--
-- Name: COLUMN fundamental_stock_basic.list_status; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.list_status IS '上市状态 L/D/P';


--
-- Name: COLUMN fundamental_stock_basic.is_hs; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.is_hs IS '沪深港通 N/H/S';


--
-- Name: COLUMN fundamental_stock_basic.act_name; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.act_name IS '实控人名称';


--
-- Name: COLUMN fundamental_stock_basic.act_ent_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.act_ent_type IS '实控人企业性质';


--
-- Name: COLUMN fundamental_stock_basic.total_shares; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_stock_basic.total_shares IS '总股本（股）';


--
-- Name: fundamental_stock_concept_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.fundamental_stock_concept_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_stock_concept_id_seq OWNER TO zhouch;

--
-- Name: fundamental_stock_concept; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_stock_concept (
    id integer DEFAULT nextval('public.fundamental_stock_concept_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    concept_id integer NOT NULL,
    name character varying(100),
    source character varying(10) DEFAULT 'ths'::character varying NOT NULL,
    reason text,
    synced_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fundamental_stock_concept OWNER TO zhouch;

--
-- Name: fundamental_top10_floatholders_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_top10_floatholders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_top10_floatholders_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_top10_floatholders; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_top10_floatholders (
    id integer DEFAULT nextval('public.fundamental_top10_floatholders_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    ann_date date,
    end_date date,
    holder_name character varying(128) NOT NULL,
    hold_amount double precision,
    hold_ratio double precision,
    hold_change double precision,
    holder_type character varying(32),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    hold_float_ratio double precision
);


ALTER TABLE public.fundamental_top10_floatholders OWNER TO zhouch;

--
-- Name: COLUMN fundamental_top10_floatholders.hold_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_top10_floatholders.hold_ratio IS '占流通股本比例%';


--
-- Name: fundamental_top10_holders_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.fundamental_top10_holders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fundamental_top10_holders_id_seq OWNER TO pg_database_owner;

--
-- Name: fundamental_top10_holders; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fundamental_top10_holders (
    id integer DEFAULT nextval('public.fundamental_top10_holders_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    ann_date date,
    end_date date,
    holder_name character varying(128) NOT NULL,
    hold_amount double precision,
    hold_ratio double precision,
    hold_float_ratio double precision,
    hold_change double precision,
    holder_type character varying(32),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fundamental_top10_holders OWNER TO zhouch;

--
-- Name: COLUMN fundamental_top10_holders.hold_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_top10_holders.hold_amount IS '持有数量';


--
-- Name: COLUMN fundamental_top10_holders.hold_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_top10_holders.hold_ratio IS '占总股本比例%';


--
-- Name: COLUMN fundamental_top10_holders.hold_float_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_top10_holders.hold_float_ratio IS '占流通股本比例%';


--
-- Name: COLUMN fundamental_top10_holders.hold_change; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_top10_holders.hold_change IS '持股变化';


--
-- Name: COLUMN fundamental_top10_holders.holder_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fundamental_top10_holders.holder_type IS '股东类型';


--
-- Name: news_article_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.news_article_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.news_article_id_seq OWNER TO zhouch;

--
-- Name: news_article; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.news_article (
    id bigint DEFAULT nextval('public.news_article_id_seq'::regclass) NOT NULL,
    published_at timestamp without time zone NOT NULL,
    source character varying(32),
    channels text,
    title character varying(512) NOT NULL,
    content text,
    url character varying(1024),
    symbols character varying(10)[],
    sentiment character varying(16),
    category character varying(32),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.news_article OWNER TO zhouch;

--
-- Name: tech_adj_factor_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.tech_adj_factor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tech_adj_factor_id_seq OWNER TO pg_database_owner;

--
-- Name: tech_adj_factor; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.tech_adj_factor (
    id integer DEFAULT nextval('public.tech_adj_factor_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    trade_date date NOT NULL,
    adj_factor double precision NOT NULL,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tech_adj_factor OWNER TO zhouch;

--
-- Name: COLUMN tech_adj_factor.adj_factor; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.tech_adj_factor.adj_factor IS '复权因子';


--
-- Name: tech_daily_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.tech_daily_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tech_daily_id_seq OWNER TO pg_database_owner;

--
-- Name: tech_daily; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.tech_daily (
    id integer DEFAULT nextval('public.tech_daily_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(50),
    date date NOT NULL,
    open double precision NOT NULL,
    high double precision NOT NULL,
    low double precision NOT NULL,
    close double precision NOT NULL,
    volume integer NOT NULL,
    amount double precision NOT NULL,
    change_pct double precision,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tech_daily OWNER TO zhouch;

--
-- Name: tech_namechange_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.tech_namechange_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tech_namechange_id_seq OWNER TO pg_database_owner;

--
-- Name: tech_namechange; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.tech_namechange (
    id integer DEFAULT nextval('public.tech_namechange_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(64) NOT NULL,
    start_date date NOT NULL,
    end_date date,
    ann_date date,
    change_reason character varying(64),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tech_namechange OWNER TO zhouch;

--
-- Name: tech_suspend_d_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.tech_suspend_d_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tech_suspend_d_id_seq OWNER TO pg_database_owner;

--
-- Name: tech_suspend_d; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.tech_suspend_d (
    id integer DEFAULT nextval('public.tech_suspend_d_id_seq'::regclass) NOT NULL,
    symbol character varying(10) NOT NULL,
    trade_date date NOT NULL,
    suspend_timing character varying(32),
    suspend_type character varying(8),
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tech_suspend_d OWNER TO zhouch;

--
-- Name: COLUMN tech_suspend_d.suspend_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.tech_suspend_d.suspend_type IS 'S=停牌/R=复牌';


--
-- Name: tech_trade_cal_id_seq; Type: SEQUENCE; Schema: public; Owner: pg_database_owner
--

CREATE SEQUENCE public.tech_trade_cal_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tech_trade_cal_id_seq OWNER TO pg_database_owner;

--
-- Name: tech_trade_cal; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.tech_trade_cal (
    id integer DEFAULT nextval('public.tech_trade_cal_id_seq'::regclass) NOT NULL,
    exchange character varying(16) NOT NULL,
    cal_date date NOT NULL,
    is_open boolean DEFAULT true NOT NULL,
    pretrade_date date,
    data_source character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tech_trade_cal OWNER TO zhouch;

--
-- Name: capital_block_trade capital_block_trade_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_block_trade
    ADD CONSTRAINT capital_block_trade_pkey PRIMARY KEY (id);


--
-- Name: capital_stk_holdernumber capital_holder_num_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_stk_holdernumber
    ADD CONSTRAINT capital_holder_num_pkey PRIMARY KEY (id);


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
-- Name: capital_margin_detail capital_margin_detail_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_margin_detail
    ADD CONSTRAINT capital_margin_detail_pkey PRIMARY KEY (id);


--
-- Name: capital_margin capital_margin_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_margin
    ADD CONSTRAINT capital_margin_pkey PRIMARY KEY (id);


--
-- Name: capital_moneyflow_hsgt capital_moneyflow_hsgt_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_moneyflow_hsgt
    ADD CONSTRAINT capital_moneyflow_hsgt_pkey PRIMARY KEY (id);


--
-- Name: capital_moneyflow capital_moneyflow_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_moneyflow
    ADD CONSTRAINT capital_moneyflow_pkey PRIMARY KEY (id);


--
-- Name: capital_top_inst capital_top_inst_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_top_inst
    ADD CONSTRAINT capital_top_inst_pkey PRIMARY KEY (id);


--
-- Name: capital_top_list capital_top_list_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_top_list
    ADD CONSTRAINT capital_top_list_pkey PRIMARY KEY (id);


--
-- Name: fundamental_concept_index fundamental_concept_index_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_concept_index
    ADD CONSTRAINT fundamental_concept_index_pkey PRIMARY KEY (id);


--
-- Name: fundamental_concept_member fundamental_concept_member_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_concept_member
    ADD CONSTRAINT fundamental_concept_member_pkey PRIMARY KEY (symbol, concept_id);


--
-- Name: fundamental_concept fundamental_concept_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_concept
    ADD CONSTRAINT fundamental_concept_pkey PRIMARY KEY (id);


--
-- Name: fundamental_concept_snapshot fundamental_concept_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_concept_snapshot
    ADD CONSTRAINT fundamental_concept_snapshot_pkey PRIMARY KEY (id);


--
-- Name: fundamental_daily_basic fundamental_daily_basic_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_daily_basic
    ADD CONSTRAINT fundamental_daily_basic_pkey PRIMARY KEY (id);


--
-- Name: fundamental_dividend fundamental_dividend_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_dividend
    ADD CONSTRAINT fundamental_dividend_pkey PRIMARY KEY (id);


--
-- Name: fundamental_index_member fundamental_index_member_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_index_member
    ADD CONSTRAINT fundamental_index_member_pkey PRIMARY KEY (id);


--
-- Name: fundamental_index_daily fundamental_market_daily_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_index_daily
    ADD CONSTRAINT fundamental_market_daily_pkey PRIMARY KEY (id);


--
-- Name: fundamental_market_daily fundamental_market_daily_pkey1; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_market_daily
    ADD CONSTRAINT fundamental_market_daily_pkey1 PRIMARY KEY (id);


--
-- Name: fundamental_income fundamental_report_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_income
    ADD CONSTRAINT fundamental_report_pkey PRIMARY KEY (id);


--
-- Name: fundamental_sector_daily fundamental_sector_daily_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_sector_daily
    ADD CONSTRAINT fundamental_sector_daily_pkey PRIMARY KEY (id);


--
-- Name: fundamental_stock_basic fundamental_stock_basic_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_stock_basic
    ADD CONSTRAINT fundamental_stock_basic_pkey PRIMARY KEY (id);


--
-- Name: fundamental_stock_basic fundamental_stock_basic_symbol_key; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_stock_basic
    ADD CONSTRAINT fundamental_stock_basic_symbol_key UNIQUE (symbol);


--
-- Name: fundamental_stock_concept fundamental_stock_concept_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_stock_concept
    ADD CONSTRAINT fundamental_stock_concept_pkey PRIMARY KEY (id);


--
-- Name: fundamental_top10_floatholders fundamental_top10_float_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_top10_floatholders
    ADD CONSTRAINT fundamental_top10_float_pkey PRIMARY KEY (id);


--
-- Name: fundamental_top10_holders fundamental_top10_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_top10_holders
    ADD CONSTRAINT fundamental_top10_pkey PRIMARY KEY (id);


--
-- Name: news_article news_article_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.news_article
    ADD CONSTRAINT news_article_pkey PRIMARY KEY (id);


--
-- Name: tech_adj_factor tech_adj_factor_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_adj_factor
    ADD CONSTRAINT tech_adj_factor_pkey PRIMARY KEY (id);


--
-- Name: tech_trade_cal tech_calendar_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_trade_cal
    ADD CONSTRAINT tech_calendar_pkey PRIMARY KEY (id);


--
-- Name: tech_daily tech_kline_daily_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_daily
    ADD CONSTRAINT tech_kline_daily_pkey PRIMARY KEY (id);


--
-- Name: tech_namechange tech_name_change_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_namechange
    ADD CONSTRAINT tech_name_change_pkey PRIMARY KEY (id);


--
-- Name: tech_suspend_d tech_suspend_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_suspend_d
    ADD CONSTRAINT tech_suspend_pkey PRIMARY KEY (id);


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
-- Name: capital_margin_detail uq_capital_margin_detail_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_margin_detail
    ADD CONSTRAINT uq_capital_margin_detail_uk UNIQUE (symbol, trade_date);


--
-- Name: capital_margin uq_capital_margin_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_margin
    ADD CONSTRAINT uq_capital_margin_uk UNIQUE (exchange_id, trade_date);


--
-- Name: capital_moneyflow_hsgt uq_capital_moneyflow_hsgt_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_moneyflow_hsgt
    ADD CONSTRAINT uq_capital_moneyflow_hsgt_uk UNIQUE (trade_date);


--
-- Name: capital_moneyflow uq_capital_moneyflow_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_moneyflow
    ADD CONSTRAINT uq_capital_moneyflow_uk UNIQUE (symbol, trade_date);


--
-- Name: capital_stk_holdernumber uq_capital_stk_holdernumber_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_stk_holdernumber
    ADD CONSTRAINT uq_capital_stk_holdernumber_uk UNIQUE (symbol, end_date);


--
-- Name: capital_top_list uq_capital_top_list_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.capital_top_list
    ADD CONSTRAINT uq_capital_top_list_uk UNIQUE (trade_date, symbol, reason);


--
-- Name: fundamental_concept uq_fundamental_concept_index_code; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_concept
    ADD CONSTRAINT uq_fundamental_concept_index_code UNIQUE (index_code);


--
-- Name: fundamental_concept_index uq_fundamental_concept_index_code_date; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_concept_index
    ADD CONSTRAINT uq_fundamental_concept_index_code_date UNIQUE (index_code, trade_date);


--
-- Name: fundamental_daily_basic uq_fundamental_daily_basic_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_daily_basic
    ADD CONSTRAINT uq_fundamental_daily_basic_uk UNIQUE (symbol, trade_date);


--
-- Name: fundamental_dividend uq_fundamental_dividend_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_dividend
    ADD CONSTRAINT uq_fundamental_dividend_uk UNIQUE (symbol, end_date, div_proc);


--
-- Name: fundamental_income uq_fundamental_income_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_income
    ADD CONSTRAINT uq_fundamental_income_uk UNIQUE (symbol, end_date, report_type);


--
-- Name: fundamental_index_daily uq_fundamental_index_daily_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_index_daily
    ADD CONSTRAINT uq_fundamental_index_daily_uk UNIQUE (market, trade_date);


--
-- Name: fundamental_index_member uq_fundamental_index_member_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_index_member
    ADD CONSTRAINT uq_fundamental_index_member_uk UNIQUE (sector_type, sector_code, symbol, effective_date);


--
-- Name: fundamental_market_daily uq_fundamental_market_daily_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_market_daily
    ADD CONSTRAINT uq_fundamental_market_daily_uk UNIQUE (market, trade_date);


--
-- Name: fundamental_sector_daily uq_fundamental_sector_daily_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_sector_daily
    ADD CONSTRAINT uq_fundamental_sector_daily_uk UNIQUE (sector_type, sector_code, trade_date);


--
-- Name: fundamental_stock_concept uq_fundamental_stock_concept_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_stock_concept
    ADD CONSTRAINT uq_fundamental_stock_concept_uk UNIQUE (symbol, concept_id);


--
-- Name: fundamental_top10_floatholders uq_fundamental_top10_floatholders_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_top10_floatholders
    ADD CONSTRAINT uq_fundamental_top10_floatholders_uk UNIQUE (symbol, end_date, ann_date, holder_name);


--
-- Name: fundamental_top10_holders uq_fundamental_top10_holders_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fundamental_top10_holders
    ADD CONSTRAINT uq_fundamental_top10_holders_uk UNIQUE (symbol, end_date, ann_date, holder_name);


--
-- Name: news_article uq_news_article_source_url; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.news_article
    ADD CONSTRAINT uq_news_article_source_url UNIQUE (source, url);


--
-- Name: tech_adj_factor uq_tech_adj_factor_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_adj_factor
    ADD CONSTRAINT uq_tech_adj_factor_uk UNIQUE (symbol, trade_date);


--
-- Name: tech_daily uq_tech_daily_symbol_date; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_daily
    ADD CONSTRAINT uq_tech_daily_symbol_date UNIQUE (symbol, date);


--
-- Name: tech_namechange uq_tech_namechange_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_namechange
    ADD CONSTRAINT uq_tech_namechange_uk UNIQUE (symbol, start_date);


--
-- Name: tech_trade_cal uq_tech_trade_cal_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_trade_cal
    ADD CONSTRAINT uq_tech_trade_cal_uk UNIQUE (cal_date, exchange);


--
-- Name: ix_capital_block_trade_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_block_trade_date ON public.capital_block_trade USING btree (trade_date);


--
-- Name: ix_capital_block_trade_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_block_trade_symbol ON public.capital_block_trade USING btree (symbol);


--
-- Name: ix_capital_block_trade_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_block_trade_symbol_date ON public.capital_block_trade USING btree (symbol, trade_date);


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
-- Name: ix_capital_margin_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_margin_date ON public.capital_margin USING btree (trade_date);


--
-- Name: ix_capital_margin_detail_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_margin_detail_date ON public.capital_margin_detail USING btree (trade_date);


--
-- Name: ix_capital_margin_detail_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_margin_detail_symbol ON public.capital_margin_detail USING btree (symbol);


--
-- Name: ix_capital_margin_detail_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_margin_detail_symbol_date ON public.capital_margin_detail USING btree (symbol, trade_date);


--
-- Name: ix_capital_moneyflow_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_moneyflow_date ON public.capital_moneyflow USING btree (trade_date);


--
-- Name: ix_capital_moneyflow_hsgt_trade_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_moneyflow_hsgt_trade_date ON public.capital_moneyflow_hsgt USING btree (trade_date);


--
-- Name: ix_capital_moneyflow_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_moneyflow_symbol ON public.capital_moneyflow USING btree (symbol);


--
-- Name: ix_capital_moneyflow_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_moneyflow_symbol_date ON public.capital_moneyflow USING btree (symbol, trade_date);


--
-- Name: ix_capital_stk_holdernumber_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_stk_holdernumber_date ON public.capital_stk_holdernumber USING btree (end_date);


--
-- Name: ix_capital_stk_holdernumber_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_stk_holdernumber_symbol ON public.capital_stk_holdernumber USING btree (symbol);


--
-- Name: ix_capital_top_inst_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_top_inst_date ON public.capital_top_inst USING btree (trade_date);


--
-- Name: ix_capital_top_inst_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_top_inst_symbol ON public.capital_top_inst USING btree (symbol);


--
-- Name: ix_capital_top_inst_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_top_inst_symbol_date ON public.capital_top_inst USING btree (symbol, trade_date);


--
-- Name: ix_capital_top_list_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_top_list_date ON public.capital_top_list USING btree (trade_date);


--
-- Name: ix_capital_top_list_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_top_list_symbol ON public.capital_top_list USING btree (symbol);


--
-- Name: ix_capital_top_list_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_capital_top_list_symbol_date ON public.capital_top_list USING btree (symbol, trade_date);


--
-- Name: ix_fundamental_concept_active; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_concept_active ON public.fundamental_concept USING btree (is_active) WHERE (is_active = true);


--
-- Name: ix_fundamental_concept_index_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_concept_index_date ON public.fundamental_concept_index USING btree (trade_date);


--
-- Name: ix_fundamental_concept_index_name; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_concept_index_name ON public.fundamental_concept_index USING btree (concept_name);


--
-- Name: ix_fundamental_concept_member_concept; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_concept_member_concept ON public.fundamental_concept_member USING btree (concept_id);


--
-- Name: ix_fundamental_concept_member_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_concept_member_symbol ON public.fundamental_concept_member USING btree (symbol);


--
-- Name: ix_fundamental_concept_name; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_concept_name ON public.fundamental_concept USING btree (name);


--
-- Name: ix_fundamental_concept_snapshot_code_captured; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_concept_snapshot_code_captured ON public.fundamental_concept_snapshot USING btree (index_code, captured_at);


--
-- Name: ix_fundamental_concept_snapshot_name_captured; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_concept_snapshot_name_captured ON public.fundamental_concept_snapshot USING btree (concept_name, captured_at);


--
-- Name: ix_fundamental_daily_basic_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_daily_basic_date ON public.fundamental_daily_basic USING btree (trade_date);


--
-- Name: ix_fundamental_daily_basic_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_daily_basic_symbol ON public.fundamental_daily_basic USING btree (symbol);


--
-- Name: ix_fundamental_daily_basic_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_daily_basic_symbol_date ON public.fundamental_daily_basic USING btree (symbol, trade_date);


--
-- Name: ix_fundamental_dividend_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_dividend_date ON public.fundamental_dividend USING btree (end_date);


--
-- Name: ix_fundamental_dividend_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_dividend_symbol ON public.fundamental_dividend USING btree (symbol);


--
-- Name: ix_fundamental_income_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_income_symbol ON public.fundamental_income USING btree (symbol);


--
-- Name: ix_fundamental_income_symbol_end; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_income_symbol_end ON public.fundamental_income USING btree (symbol, end_date);


--
-- Name: ix_fundamental_index_daily_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_index_daily_date ON public.fundamental_index_daily USING btree (trade_date);


--
-- Name: ix_fundamental_index_daily_market_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_index_daily_market_date ON public.fundamental_index_daily USING btree (market, trade_date);


--
-- Name: ix_fundamental_index_member_sector; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_index_member_sector ON public.fundamental_index_member USING btree (sector_type, sector_code);


--
-- Name: ix_fundamental_index_member_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_index_member_symbol ON public.fundamental_index_member USING btree (symbol);


--
-- Name: ix_fundamental_market_daily_trade_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_market_daily_trade_date ON public.fundamental_market_daily USING btree (trade_date);


--
-- Name: ix_fundamental_sector_daily_code; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_sector_daily_code ON public.fundamental_sector_daily USING btree (sector_code);


--
-- Name: ix_fundamental_sector_daily_type_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_sector_daily_type_date ON public.fundamental_sector_daily USING btree (sector_type, trade_date);


--
-- Name: ix_fundamental_stock_basic_area; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_basic_area ON public.fundamental_stock_basic USING btree (area);


--
-- Name: ix_fundamental_stock_basic_exchange; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_basic_exchange ON public.fundamental_stock_basic USING btree (exchange);


--
-- Name: ix_fundamental_stock_basic_industry; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_basic_industry ON public.fundamental_stock_basic USING btree (industry);


--
-- Name: ix_fundamental_stock_basic_list_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_basic_list_status ON public.fundamental_stock_basic USING btree (list_status);


--
-- Name: ix_fundamental_stock_basic_market; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_basic_market ON public.fundamental_stock_basic USING btree (market);


--
-- Name: ix_fundamental_stock_basic_name; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_basic_name ON public.fundamental_stock_basic USING btree (name);


--
-- Name: ix_fundamental_stock_basic_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_basic_symbol ON public.fundamental_stock_basic USING btree (symbol);


--
-- Name: ix_fundamental_stock_basic_ts_code; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_basic_ts_code ON public.fundamental_stock_basic USING btree (ts_code);


--
-- Name: ix_fundamental_stock_concept_concept_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_concept_concept_id ON public.fundamental_stock_concept USING btree (concept_id);


--
-- Name: ix_fundamental_stock_concept_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_stock_concept_symbol ON public.fundamental_stock_concept USING btree (symbol);


--
-- Name: ix_fundamental_top10_floatholders_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_top10_floatholders_date ON public.fundamental_top10_floatholders USING btree (end_date);


--
-- Name: ix_fundamental_top10_floatholders_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_top10_floatholders_symbol ON public.fundamental_top10_floatholders USING btree (symbol);


--
-- Name: ix_fundamental_top10_holders_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_top10_holders_date ON public.fundamental_top10_holders USING btree (end_date);


--
-- Name: ix_fundamental_top10_holders_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fundamental_top10_holders_symbol ON public.fundamental_top10_holders USING btree (symbol);


--
-- Name: ix_news_article_published_at; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_news_article_published_at ON public.news_article USING btree (published_at);


--
-- Name: ix_news_article_source; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_news_article_source ON public.news_article USING btree (source);


--
-- Name: ix_news_article_symbols; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_news_article_symbols ON public.news_article USING gin (symbols);


--
-- Name: ix_stock_basic_exchange_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_basic_exchange_status ON public.fundamental_stock_basic USING btree (exchange, list_status);


--
-- Name: ix_stock_basic_industry_market; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_basic_industry_market ON public.fundamental_stock_basic USING btree (industry, market);


--
-- Name: ix_tech_adj_factor_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_adj_factor_date ON public.tech_adj_factor USING btree (trade_date);


--
-- Name: ix_tech_adj_factor_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_adj_factor_symbol ON public.tech_adj_factor USING btree (symbol);


--
-- Name: ix_tech_adj_factor_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_adj_factor_symbol_date ON public.tech_adj_factor USING btree (symbol, trade_date);


--
-- Name: ix_tech_daily_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_daily_symbol ON public.tech_daily USING btree (symbol);


--
-- Name: ix_tech_daily_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_daily_symbol_date ON public.tech_daily USING btree (symbol, date);


--
-- Name: ix_tech_namechange_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_namechange_symbol ON public.tech_namechange USING btree (symbol);


--
-- Name: ix_tech_suspend_d_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_suspend_d_date ON public.tech_suspend_d USING btree (trade_date);


--
-- Name: ix_tech_suspend_d_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_suspend_d_symbol ON public.tech_suspend_d USING btree (symbol);


--
-- Name: ix_tech_suspend_d_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_suspend_d_symbol_date ON public.tech_suspend_d USING btree (symbol, trade_date);


--
-- Name: ix_tech_trade_cal_exchange; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_trade_cal_exchange ON public.tech_trade_cal USING btree (exchange);


--
-- Name: ix_tech_trade_cal_exchange_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_trade_cal_exchange_date ON public.tech_trade_cal USING btree (exchange, cal_date);


--
-- PostgreSQL database dump complete
--

\unrestrict rCjVjD0sDMIRyNbnPVMX1Uwn7vx3R5I8bboZzEaHnsmycIpxa5XN3QFzF1f7ja6

