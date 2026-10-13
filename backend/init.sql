--
-- PostgreSQL database dump
--

\restrict 61FCHjRpDjbQXb6PfLvxFeTIsB4VHnRsKXiOfe154pUAgPKcaUyUeznVJGWWkon

-- Dumped from database version 16.15
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: base_adj_factors; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.base_adj_factors (
    id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    trade_date date NOT NULL,
    adj_factor double precision NOT NULL,
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.base_adj_factors OWNER TO zhouch;

--
-- Name: COLUMN base_adj_factors.adj_factor; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.base_adj_factors.adj_factor IS '复权因子';


--
-- Name: base_adj_factors_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.base_adj_factors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.base_adj_factors_id_seq OWNER TO zhouch;

--
-- Name: base_adj_factors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.base_adj_factors_id_seq OWNED BY public.base_adj_factors.id;


--
-- Name: base_dividends; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.base_dividends (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.base_dividends OWNER TO zhouch;

--
-- Name: COLUMN base_dividends.div_proc; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.base_dividends.div_proc IS '实施进度';


--
-- Name: COLUMN base_dividends.stk_div; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.base_dividends.stk_div IS '每股送股';


--
-- Name: COLUMN base_dividends.stk_bo_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.base_dividends.stk_bo_rate IS '每股转增比例';


--
-- Name: COLUMN base_dividends.stk_co_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.base_dividends.stk_co_rate IS '每股送股比例';


--
-- Name: COLUMN base_dividends.cash_div; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.base_dividends.cash_div IS '每股派息(税前)';


--
-- Name: COLUMN base_dividends.cash_div_tax; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.base_dividends.cash_div_tax IS '每股派息(税后)';


--
-- Name: base_dividends_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.base_dividends_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.base_dividends_id_seq OWNER TO zhouch;

--
-- Name: base_dividends_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.base_dividends_id_seq OWNED BY public.base_dividends.id;


--
-- Name: base_name_changes; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.base_name_changes (
    id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(64) NOT NULL,
    start_date date NOT NULL,
    end_date date,
    ann_date date,
    change_reason character varying(64),
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.base_name_changes OWNER TO zhouch;

--
-- Name: base_name_changes_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.base_name_changes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.base_name_changes_id_seq OWNER TO zhouch;

--
-- Name: base_name_changes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.base_name_changes_id_seq OWNED BY public.base_name_changes.id;


--
-- Name: base_suspends; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.base_suspends (
    id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    trade_date date NOT NULL,
    suspend_timing date,
    suspend_type character varying(8),
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.base_suspends OWNER TO zhouch;

--
-- Name: COLUMN base_suspends.suspend_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.base_suspends.suspend_type IS 'S=停牌/R=复牌';


--
-- Name: base_suspends_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.base_suspends_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.base_suspends_id_seq OWNER TO zhouch;

--
-- Name: base_suspends_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.base_suspends_id_seq OWNED BY public.base_suspends.id;


--
-- Name: cap_block_trades; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.cap_block_trades (
    id integer NOT NULL,
    trade_date date NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(50),
    price double precision,
    vol double precision,
    amount double precision,
    buyer character varying(128),
    seller character varying(128),
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cap_block_trades OWNER TO zhouch;

--
-- Name: COLUMN cap_block_trades.price; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_block_trades.price IS '成交价';


--
-- Name: COLUMN cap_block_trades.vol; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_block_trades.vol IS '成交量(万股)';


--
-- Name: COLUMN cap_block_trades.amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_block_trades.amount IS '成交金额';


--
-- Name: COLUMN cap_block_trades.buyer; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_block_trades.buyer IS '买方营业部';


--
-- Name: COLUMN cap_block_trades.seller; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_block_trades.seller IS '卖方营业部';


--
-- Name: cap_block_trades_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.cap_block_trades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cap_block_trades_id_seq OWNER TO zhouch;

--
-- Name: cap_block_trades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.cap_block_trades_id_seq OWNED BY public.cap_block_trades.id;


--
-- Name: cap_holder_nums; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.cap_holder_nums (
    id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    ann_date date,
    end_date date NOT NULL,
    holder_num integer,
    holder_nums double precision,
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cap_holder_nums OWNER TO zhouch;

--
-- Name: COLUMN cap_holder_nums.holder_num; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_holder_nums.holder_num IS '股东户数';


--
-- Name: COLUMN cap_holder_nums.holder_nums; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_holder_nums.holder_nums IS '股东户数(详细)';


--
-- Name: cap_holder_nums_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.cap_holder_nums_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cap_holder_nums_id_seq OWNER TO zhouch;

--
-- Name: cap_holder_nums_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.cap_holder_nums_id_seq OWNED BY public.cap_holder_nums.id;


--
-- Name: cap_margin_details; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.cap_margin_details (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cap_margin_details OWNER TO zhouch;

--
-- Name: COLUMN cap_margin_details.rzye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margin_details.rzye IS '融资余额';


--
-- Name: COLUMN cap_margin_details.rqye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margin_details.rqye IS '融券余额';


--
-- Name: COLUMN cap_margin_details.rzmre; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margin_details.rzmre IS '融资买入额';


--
-- Name: COLUMN cap_margin_details.rqyl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margin_details.rqyl IS '融券余量';


--
-- Name: COLUMN cap_margin_details.rzche; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margin_details.rzche IS '融资偿还额';


--
-- Name: COLUMN cap_margin_details.rqchl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margin_details.rqchl IS '融券偿还量';


--
-- Name: COLUMN cap_margin_details.rqmcl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margin_details.rqmcl IS '融券卖出量';


--
-- Name: COLUMN cap_margin_details.rzrqye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margin_details.rzrqye IS '融资融券余额';


--
-- Name: cap_margin_details_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.cap_margin_details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cap_margin_details_id_seq OWNER TO zhouch;

--
-- Name: cap_margin_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.cap_margin_details_id_seq OWNED BY public.cap_margin_details.id;


--
-- Name: cap_margins; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.cap_margins (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cap_margins OWNER TO zhouch;

--
-- Name: COLUMN cap_margins.exchange_id; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margins.exchange_id IS '交易所代码 SSE/SZSE';


--
-- Name: COLUMN cap_margins.rzye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margins.rzye IS '融资余额(元)';


--
-- Name: COLUMN cap_margins.rzmre; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margins.rzmre IS '融资买入额(元)';


--
-- Name: COLUMN cap_margins.rzche; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margins.rzche IS '融资偿还额(元)';


--
-- Name: COLUMN cap_margins.rqye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margins.rqye IS '融券余额(元)';


--
-- Name: COLUMN cap_margins.rqmcl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margins.rqmcl IS '融券卖出量(股)';


--
-- Name: COLUMN cap_margins.rzrqye; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margins.rzrqye IS '融资融券余额(元)';


--
-- Name: COLUMN cap_margins.rqyl; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_margins.rqyl IS '融券余量(股)';


--
-- Name: cap_margins_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.cap_margins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cap_margins_id_seq OWNER TO zhouch;

--
-- Name: cap_margins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.cap_margins_id_seq OWNED BY public.cap_margins.id;


--
-- Name: cap_moneyflows; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.cap_moneyflows (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cap_moneyflows OWNER TO zhouch;

--
-- Name: cap_moneyflows_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.cap_moneyflows_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cap_moneyflows_id_seq OWNER TO zhouch;

--
-- Name: cap_moneyflows_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.cap_moneyflows_id_seq OWNED BY public.cap_moneyflows.id;


--
-- Name: cap_top_insts; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.cap_top_insts (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cap_top_insts OWNER TO zhouch;

--
-- Name: COLUMN cap_top_insts.exalter; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_insts.exalter IS '营业部名称';


--
-- Name: COLUMN cap_top_insts.side; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_insts.side IS '买卖方向: 0=卖/1=买';


--
-- Name: COLUMN cap_top_insts.buy; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_insts.buy IS '买入额';


--
-- Name: COLUMN cap_top_insts.buy_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_insts.buy_rate IS '买入占总成交比';


--
-- Name: COLUMN cap_top_insts.sell; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_insts.sell IS '卖出额';


--
-- Name: COLUMN cap_top_insts.sell_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_insts.sell_rate IS '卖出占总成交比';


--
-- Name: COLUMN cap_top_insts.net_buy; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_insts.net_buy IS '净额';


--
-- Name: COLUMN cap_top_insts.reason; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_insts.reason IS '上榜原因';


--
-- Name: cap_top_insts_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.cap_top_insts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cap_top_insts_id_seq OWNER TO zhouch;

--
-- Name: cap_top_insts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.cap_top_insts_id_seq OWNED BY public.cap_top_insts.id;


--
-- Name: cap_top_lists; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.cap_top_lists (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cap_top_lists OWNER TO zhouch;

--
-- Name: COLUMN cap_top_lists.l_sell; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_lists.l_sell IS '龙虎榜卖出额';


--
-- Name: COLUMN cap_top_lists.l_buy; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_lists.l_buy IS '龙虎榜买入额';


--
-- Name: COLUMN cap_top_lists.l_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_lists.l_amount IS '龙虎榜成交额';


--
-- Name: COLUMN cap_top_lists.net_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_lists.net_amount IS '净买入额';


--
-- Name: COLUMN cap_top_lists.net_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_lists.net_rate IS '净买/总成交';


--
-- Name: COLUMN cap_top_lists.amount_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_lists.amount_rate IS '成交额占比';


--
-- Name: COLUMN cap_top_lists.float_values; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_lists.float_values IS '流通市值';


--
-- Name: COLUMN cap_top_lists.reason; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.cap_top_lists.reason IS '上榜原因';


--
-- Name: cap_top_lists_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.cap_top_lists_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cap_top_lists_id_seq OWNER TO zhouch;

--
-- Name: cap_top_lists_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.cap_top_lists_id_seq OWNED BY public.cap_top_lists.id;


--
-- Name: collect_fetchers; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_fetchers (
    task_type character varying(64) NOT NULL,
    label character varying(64) NOT NULL,
    facet character varying(32) NOT NULL,
    sub_facet character varying(32) NOT NULL,
    description character varying(255) NOT NULL,
    kind character varying(16) NOT NULL,
    status character varying(16) NOT NULL,
    default_params json NOT NULL,
    supports_run_one boolean NOT NULL,
    sort_order integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.collect_fetchers OWNER TO zhouch;

--
-- Name: collect_groups; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_groups (
    id integer NOT NULL,
    name character varying(64) NOT NULL,
    items json NOT NULL,
    enabled boolean NOT NULL,
    cron character varying(64),
    trading_day_only boolean NOT NULL,
    stop_on_fail boolean NOT NULL,
    last_run_at timestamp without time zone,
    last_group_run_id integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.collect_groups OWNER TO zhouch;

--
-- Name: collect_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.collect_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.collect_groups_id_seq OWNER TO zhouch;

--
-- Name: collect_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.collect_groups_id_seq OWNED BY public.collect_groups.id;


--
-- Name: collect_plan_items; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_plan_items (
    id integer NOT NULL,
    plan_id integer NOT NULL,
    task_type character varying(64) NOT NULL,
    params json NOT NULL,
    enabled boolean NOT NULL,
    sort_order integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.collect_plan_items OWNER TO zhouch;

--
-- Name: collect_plan_items_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.collect_plan_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.collect_plan_items_id_seq OWNER TO zhouch;

--
-- Name: collect_plan_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.collect_plan_items_id_seq OWNED BY public.collect_plan_items.id;


--
-- Name: collect_plans; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_plans (
    id integer NOT NULL,
    name character varying(64) NOT NULL,
    enabled boolean NOT NULL,
    schedule_type character varying(16),
    times json NOT NULL,
    interval_seconds integer,
    stop_on_fail boolean NOT NULL,
    last_run_at timestamp without time zone,
    last_task_id integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.collect_plans OWNER TO zhouch;

--
-- Name: collect_plans_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.collect_plans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.collect_plans_id_seq OWNER TO zhouch;

--
-- Name: collect_plans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.collect_plans_id_seq OWNED BY public.collect_plans.id;


--
-- Name: concept_index_ths; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.concept_index_ths (
    id integer NOT NULL,
    index_code character varying(10) NOT NULL,
    concept_name character varying(100) NOT NULL,
    trade_date date NOT NULL,
    open double precision NOT NULL,
    high double precision NOT NULL,
    low double precision NOT NULL,
    close double precision NOT NULL,
    volume bigint NOT NULL,
    amount double precision NOT NULL,
    change double precision,
    change_pct double precision,
    captured_at timestamp with time zone NOT NULL
);


ALTER TABLE public.concept_index_ths OWNER TO zhouch;

--
-- Name: concept_index_ths_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.concept_index_ths_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.concept_index_ths_id_seq OWNER TO zhouch;

--
-- Name: concept_index_ths_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.concept_index_ths_id_seq OWNED BY public.concept_index_ths.id;


--
-- Name: concept_snapshots; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.concept_snapshots (
    id integer NOT NULL,
    index_code character varying(10) NOT NULL,
    concept_name character varying(100) NOT NULL,
    trade_time timestamp without time zone,
    open_price double precision,
    high double precision,
    low double precision,
    price double precision,
    prev_close double precision,
    pct_change double precision,
    rank_current integer,
    rank_total integer,
    up_count integer,
    down_count integer,
    volume_wan double precision,
    turnover_yi double precision,
    net_inflow_yi double precision,
    source character varying(10) NOT NULL,
    captured_at timestamp with time zone NOT NULL
);


ALTER TABLE public.concept_snapshots OWNER TO zhouch;

--
-- Name: concept_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.concept_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.concept_snapshots_id_seq OWNER TO zhouch;

--
-- Name: concept_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.concept_snapshots_id_seq OWNED BY public.concept_snapshots.id;


--
-- Name: concepts; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.concepts (
    id integer NOT NULL,
    index_code character varying(10) NOT NULL,
    concept_code character varying(10),
    name character varying(100) NOT NULL,
    source character varying(10) NOT NULL,
    concept_type character varying(50) NOT NULL,
    description text,
    stock_count integer NOT NULL,
    is_active boolean NOT NULL,
    first_seen_at timestamp with time zone NOT NULL,
    last_synced_at timestamp with time zone
);


ALTER TABLE public.concepts OWNER TO zhouch;

--
-- Name: concepts_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.concepts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.concepts_id_seq OWNER TO zhouch;

--
-- Name: concepts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.concepts_id_seq OWNED BY public.concepts.id;


--
-- Name: tech_kline_dailys; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.tech_kline_dailys (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tech_kline_dailys OWNER TO zhouch;

--
-- Name: daily_klines_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.daily_klines_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.daily_klines_id_seq OWNER TO zhouch;

--
-- Name: daily_klines_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.daily_klines_id_seq OWNED BY public.tech_kline_dailys.id;


--
-- Name: fin_daily_basics; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fin_daily_basics (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fin_daily_basics OWNER TO zhouch;

--
-- Name: COLUMN fin_daily_basics.turnover_rate; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.turnover_rate IS '换手率%';


--
-- Name: COLUMN fin_daily_basics.turnover_rate_f; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.turnover_rate_f IS '换手率(自由流通)';


--
-- Name: COLUMN fin_daily_basics.volume_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.volume_ratio IS '量比';


--
-- Name: COLUMN fin_daily_basics.pe; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.pe IS '市盈率(动)';


--
-- Name: COLUMN fin_daily_basics.pe_ttm; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.pe_ttm IS '市盈率TTM';


--
-- Name: COLUMN fin_daily_basics.pb; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.pb IS '市净率';


--
-- Name: COLUMN fin_daily_basics.ps; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.ps IS '市销率';


--
-- Name: COLUMN fin_daily_basics.ps_ttm; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.ps_ttm IS '市销率TTM';


--
-- Name: COLUMN fin_daily_basics.dv_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.dv_ratio IS '股息率%';


--
-- Name: COLUMN fin_daily_basics.dv_ttm; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.dv_ttm IS '股息率TTM%';


--
-- Name: COLUMN fin_daily_basics.total_share; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.total_share IS '总股本(万股)';


--
-- Name: COLUMN fin_daily_basics.float_share; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.float_share IS '流通股本(万股)';


--
-- Name: COLUMN fin_daily_basics.free_share; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.free_share IS '自由流通股本(万股)';


--
-- Name: COLUMN fin_daily_basics.total_mv; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.total_mv IS '总市值(万元)';


--
-- Name: COLUMN fin_daily_basics.circ_mv; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_daily_basics.circ_mv IS '流通市值(万元)';


--
-- Name: fin_daily_basics_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.fin_daily_basics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fin_daily_basics_id_seq OWNER TO zhouch;

--
-- Name: fin_daily_basics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.fin_daily_basics_id_seq OWNED BY public.fin_daily_basics.id;


--
-- Name: fin_reports; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fin_reports (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fin_reports OWNER TO zhouch;

--
-- Name: COLUMN fin_reports.report_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.report_type IS '报表类型: 1=合并报表/2=母公司报表';


--
-- Name: COLUMN fin_reports.comp_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.comp_type IS '公司类型: 1=工商业/2=金融/3=保险';


--
-- Name: COLUMN fin_reports.basic_eps; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.basic_eps IS '基本每股收益';


--
-- Name: COLUMN fin_reports.diluted_eps; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.diluted_eps IS '稀释每股收益';


--
-- Name: COLUMN fin_reports.total_revenue; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.total_revenue IS '营业总收入';


--
-- Name: COLUMN fin_reports.revenue; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.revenue IS '营业收入';


--
-- Name: COLUMN fin_reports.operate_profit; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.operate_profit IS '营业利润';


--
-- Name: COLUMN fin_reports.total_profit; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.total_profit IS '利润总额';


--
-- Name: COLUMN fin_reports.n_income; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.n_income IS '净利润';


--
-- Name: COLUMN fin_reports.n_income_attr_p; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.n_income_attr_p IS '归属母公司股东的净利润';


--
-- Name: COLUMN fin_reports.total_assets; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.total_assets IS '资产总计';


--
-- Name: COLUMN fin_reports.total_liab; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.total_liab IS '负债合计';


--
-- Name: COLUMN fin_reports.total_hldr_eqy_exc_min_int; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.total_hldr_eqy_exc_min_int IS '归属母公司股东权益';


--
-- Name: COLUMN fin_reports.n_cashflow_act; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.n_cashflow_act IS '经营活动现金流量净额';


--
-- Name: COLUMN fin_reports.n_cash_flows_fnc_act; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.n_cash_flows_fnc_act IS '筹资活动现金流量净额';


--
-- Name: COLUMN fin_reports.n_cashflow_inv_act; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_reports.n_cashflow_inv_act IS '投资活动现金流量净额';


--
-- Name: fin_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.fin_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fin_reports_id_seq OWNER TO zhouch;

--
-- Name: fin_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.fin_reports_id_seq OWNED BY public.fin_reports.id;


--
-- Name: fin_top10_floatholders; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fin_top10_floatholders (
    id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    ann_date date,
    end_date date,
    holder_name character varying(128) NOT NULL,
    hold_amount double precision,
    hold_ratio double precision,
    hold_change double precision,
    holder_type character varying(32),
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fin_top10_floatholders OWNER TO zhouch;

--
-- Name: COLUMN fin_top10_floatholders.hold_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_top10_floatholders.hold_ratio IS '占流通股本比例%';


--
-- Name: fin_top10_floatholders_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.fin_top10_floatholders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fin_top10_floatholders_id_seq OWNER TO zhouch;

--
-- Name: fin_top10_floatholders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.fin_top10_floatholders_id_seq OWNED BY public.fin_top10_floatholders.id;


--
-- Name: fin_top10_holders; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.fin_top10_holders (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.fin_top10_holders OWNER TO zhouch;

--
-- Name: COLUMN fin_top10_holders.hold_amount; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_top10_holders.hold_amount IS '持有数量';


--
-- Name: COLUMN fin_top10_holders.hold_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_top10_holders.hold_ratio IS '占总股本比例%';


--
-- Name: COLUMN fin_top10_holders.hold_float_ratio; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_top10_holders.hold_float_ratio IS '占流通股本比例%';


--
-- Name: COLUMN fin_top10_holders.hold_change; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_top10_holders.hold_change IS '持股变化';


--
-- Name: COLUMN fin_top10_holders.holder_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.fin_top10_holders.holder_type IS '股东类型';


--
-- Name: fin_top10_holders_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.fin_top10_holders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fin_top10_holders_id_seq OWNER TO zhouch;

--
-- Name: fin_top10_holders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.fin_top10_holders_id_seq OWNED BY public.fin_top10_holders.id;


--
-- Name: mkt_calendars; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.mkt_calendars (
    id integer NOT NULL,
    exchange character varying(16) NOT NULL,
    cal_date date NOT NULL,
    is_open boolean NOT NULL,
    pretrade_date date,
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.mkt_calendars OWNER TO zhouch;

--
-- Name: mkt_calendars_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.mkt_calendars_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mkt_calendars_id_seq OWNER TO zhouch;

--
-- Name: mkt_calendars_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.mkt_calendars_id_seq OWNED BY public.mkt_calendars.id;


--
-- Name: mkt_index_members; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.mkt_index_members (
    id integer NOT NULL,
    sector_type character varying(16) NOT NULL,
    sector_code character varying(32) NOT NULL,
    sector_name character varying(64),
    symbol character varying(10) NOT NULL,
    name character varying(50),
    effective_date date,
    expiry_date date,
    is_new character varying(8),
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.mkt_index_members OWNER TO zhouch;

--
-- Name: COLUMN mkt_index_members.sector_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_index_members.sector_type IS '板块类型: industry/concept/area';


--
-- Name: COLUMN mkt_index_members.sector_code; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_index_members.sector_code IS '板块代码';


--
-- Name: COLUMN mkt_index_members.effective_date; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_index_members.effective_date IS '纳入日期';


--
-- Name: COLUMN mkt_index_members.expiry_date; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_index_members.expiry_date IS '剔除日期';


--
-- Name: COLUMN mkt_index_members.is_new; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_index_members.is_new IS 'Y/N';


--
-- Name: mkt_index_members_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.mkt_index_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mkt_index_members_id_seq OWNER TO zhouch;

--
-- Name: mkt_index_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.mkt_index_members_id_seq OWNED BY public.mkt_index_members.id;


--
-- Name: mkt_market_dailys; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.mkt_market_dailys (
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
    data_source character varying(16) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.mkt_market_dailys OWNER TO zhouch;

--
-- Name: COLUMN mkt_market_dailys.market; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_market_dailys.market IS '市场代码: SSE/SZSE/CSI';


--
-- Name: mkt_market_dailys_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.mkt_market_dailys_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mkt_market_dailys_id_seq OWNER TO zhouch;

--
-- Name: mkt_market_dailys_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.mkt_market_dailys_id_seq OWNED BY public.mkt_market_dailys.id;


--
-- Name: mkt_sector_dailys; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.mkt_sector_dailys (
    id integer NOT NULL,
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
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.mkt_sector_dailys OWNER TO zhouch;

--
-- Name: COLUMN mkt_sector_dailys.sector_type; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_sector_dailys.sector_type IS '板块类型: industry/concept/area';


--
-- Name: COLUMN mkt_sector_dailys.sector_code; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_sector_dailys.sector_code IS '板块代码';


--
-- Name: COLUMN mkt_sector_dailys.sector_name; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.mkt_sector_dailys.sector_name IS '板块名称';


--
-- Name: mkt_sector_dailys_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.mkt_sector_dailys_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mkt_sector_dailys_id_seq OWNER TO zhouch;

--
-- Name: mkt_sector_dailys_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.mkt_sector_dailys_id_seq OWNED BY public.mkt_sector_dailys.id;


--
-- Name: pool_operations; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.pool_operations (
    id integer NOT NULL,
    pool_id integer,
    operation_type character varying(32) NOT NULL,
    status character varying(16) NOT NULL,
    params json NOT NULL,
    result_summary json,
    progress json NOT NULL,
    error_message text,
    started_at timestamp without time zone,
    finished_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.pool_operations OWNER TO zhouch;

--
-- Name: pool_operations_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.pool_operations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pool_operations_id_seq OWNER TO zhouch;

--
-- Name: pool_operations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.pool_operations_id_seq OWNED BY public.pool_operations.id;


--
-- Name: stock_concept_members; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.stock_concept_members (
    symbol character varying(10) NOT NULL,
    concept_id integer NOT NULL,
    reason text,
    joined_at timestamp with time zone NOT NULL,
    synced_at timestamp with time zone NOT NULL,
    source character varying(10) NOT NULL
);


ALTER TABLE public.stock_concept_members OWNER TO zhouch;

--
-- Name: stock_infos; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.stock_infos (
    id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    name character varying(50),
    industry character varying(100),
    market character varying(50),
    list_date date,
    total_shares bigint,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    ts_code character varying(20),
    area character varying(50),
    exchange character varying(10),
    delist_date date,
    list_status character varying(5) DEFAULT 'L'::character varying,
    is_hs character varying(5) DEFAULT 'N'::character varying,
    act_name character varying(200),
    act_ent_type character varying(50)
);


ALTER TABLE public.stock_infos OWNER TO zhouch;

--
-- Name: stock_infos_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.stock_infos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stock_infos_id_seq OWNER TO zhouch;

--
-- Name: stock_infos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.stock_infos_id_seq OWNED BY public.stock_infos.id;


--
-- Name: stock_pool_members; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.stock_pool_members (
    pool_id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    memo character varying(255),
    sort_order integer NOT NULL,
    added_at timestamp without time zone NOT NULL
);


ALTER TABLE public.stock_pool_members OWNER TO zhouch;

--
-- Name: stock_pools; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.stock_pools (
    id integer NOT NULL,
    name character varying(64) NOT NULL,
    description character varying(255),
    pool_type character varying(32) NOT NULL,
    color character varying(16),
    icon character varying(32),
    sort_order integer NOT NULL,
    is_default boolean NOT NULL,
    is_archived boolean NOT NULL,
    owner_id integer,
    share_token character varying(64),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.stock_pools OWNER TO zhouch;

--
-- Name: stock_pools_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.stock_pools_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stock_pools_id_seq OWNER TO zhouch;

--
-- Name: stock_pools_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.stock_pools_id_seq OWNED BY public.stock_pools.id;


--
-- Name: sys_collect_task_details; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.sys_collect_task_details (
    id integer NOT NULL,
    task_id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    status character varying(16) NOT NULL,
    saved_count integer NOT NULL,
    error_message text,
    duration_ms integer,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.sys_collect_task_details OWNER TO zhouch;

--
-- Name: sys_collect_task_details_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.sys_collect_task_details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sys_collect_task_details_id_seq OWNER TO zhouch;

--
-- Name: sys_collect_task_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.sys_collect_task_details_id_seq OWNED BY public.sys_collect_task_details.id;


--
-- Name: sys_collect_tasks; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.sys_collect_tasks (
    id integer NOT NULL,
    task_type character varying(32) NOT NULL,
    trigger_type character varying(16) DEFAULT 'manual'::character varying NOT NULL,
    params jsonb,
    status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    total_count integer DEFAULT 0 NOT NULL,
    success_count integer DEFAULT 0 NOT NULL,
    fail_count integer DEFAULT 0 NOT NULL,
    skip_count integer DEFAULT 0 NOT NULL,
    started_at timestamp without time zone,
    finished_at timestamp without time zone,
    duration_ms integer,
    message text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    plan_run_id integer,
    group_run_id integer
);


ALTER TABLE public.sys_collect_tasks OWNER TO zhouch;

--
-- Name: sys_collect_tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.sys_collect_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sys_collect_tasks_id_seq OWNER TO zhouch;

--
-- Name: sys_collect_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.sys_collect_tasks_id_seq OWNED BY public.sys_collect_tasks.id;


--
-- Name: sys_permissions; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.sys_permissions (
    id integer NOT NULL,
    code character varying(64) NOT NULL,
    resource character varying(64) NOT NULL,
    action character varying(32) NOT NULL,
    name character varying(64) NOT NULL,
    description text,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.sys_permissions OWNER TO zhouch;

--
-- Name: sys_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.sys_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sys_permissions_id_seq OWNER TO zhouch;

--
-- Name: sys_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.sys_permissions_id_seq OWNED BY public.sys_permissions.id;


--
-- Name: sys_role_permissions; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.sys_role_permissions (
    id integer NOT NULL,
    role_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.sys_role_permissions OWNER TO zhouch;

--
-- Name: sys_role_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.sys_role_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sys_role_permissions_id_seq OWNER TO zhouch;

--
-- Name: sys_role_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.sys_role_permissions_id_seq OWNED BY public.sys_role_permissions.id;


--
-- Name: sys_roles; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.sys_roles (
    id integer NOT NULL,
    code character varying(64) NOT NULL,
    name character varying(64) NOT NULL,
    description text,
    is_system boolean DEFAULT false NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.sys_roles OWNER TO zhouch;

--
-- Name: sys_roles_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.sys_roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sys_roles_id_seq OWNER TO zhouch;

--
-- Name: sys_roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.sys_roles_id_seq OWNED BY public.sys_roles.id;


--
-- Name: sys_user_roles; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.sys_user_roles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    role_id integer NOT NULL,
    granted_at timestamp without time zone DEFAULT now() NOT NULL,
    granted_by integer
);


ALTER TABLE public.sys_user_roles OWNER TO zhouch;

--
-- Name: sys_user_roles_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.sys_user_roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sys_user_roles_id_seq OWNER TO zhouch;

--
-- Name: sys_user_roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.sys_user_roles_id_seq OWNED BY public.sys_user_roles.id;


--
-- Name: sys_users; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.sys_users (
    id integer NOT NULL,
    email character varying(128) NOT NULL,
    username character varying(64),
    password_hash character varying(128) NOT NULL,
    nickname character varying(64),
    avatar_url character varying(256),
    is_active boolean DEFAULT true NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    last_login_at timestamp without time zone,
    last_login_ip character varying(64),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.sys_users OWNER TO zhouch;

--
-- Name: sys_users_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.sys_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sys_users_id_seq OWNER TO zhouch;

--
-- Name: sys_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.sys_users_id_seq OWNED BY public.sys_users.id;


--
-- Name: base_adj_factors id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_adj_factors ALTER COLUMN id SET DEFAULT nextval('public.base_adj_factors_id_seq'::regclass);


--
-- Name: base_dividends id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_dividends ALTER COLUMN id SET DEFAULT nextval('public.base_dividends_id_seq'::regclass);


--
-- Name: base_name_changes id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_name_changes ALTER COLUMN id SET DEFAULT nextval('public.base_name_changes_id_seq'::regclass);


--
-- Name: base_suspends id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_suspends ALTER COLUMN id SET DEFAULT nextval('public.base_suspends_id_seq'::regclass);


--
-- Name: cap_block_trades id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_block_trades ALTER COLUMN id SET DEFAULT nextval('public.cap_block_trades_id_seq'::regclass);


--
-- Name: cap_holder_nums id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_holder_nums ALTER COLUMN id SET DEFAULT nextval('public.cap_holder_nums_id_seq'::regclass);


--
-- Name: cap_margin_details id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_margin_details ALTER COLUMN id SET DEFAULT nextval('public.cap_margin_details_id_seq'::regclass);


--
-- Name: cap_margins id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_margins ALTER COLUMN id SET DEFAULT nextval('public.cap_margins_id_seq'::regclass);


--
-- Name: cap_moneyflows id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_moneyflows ALTER COLUMN id SET DEFAULT nextval('public.cap_moneyflows_id_seq'::regclass);


--
-- Name: cap_top_insts id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_top_insts ALTER COLUMN id SET DEFAULT nextval('public.cap_top_insts_id_seq'::regclass);


--
-- Name: cap_top_lists id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_top_lists ALTER COLUMN id SET DEFAULT nextval('public.cap_top_lists_id_seq'::regclass);


--
-- Name: collect_groups id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_groups ALTER COLUMN id SET DEFAULT nextval('public.collect_groups_id_seq'::regclass);


--
-- Name: collect_plan_items id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_plan_items ALTER COLUMN id SET DEFAULT nextval('public.collect_plan_items_id_seq'::regclass);


--
-- Name: collect_plans id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_plans ALTER COLUMN id SET DEFAULT nextval('public.collect_plans_id_seq'::regclass);


--
-- Name: concept_index_ths id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.concept_index_ths ALTER COLUMN id SET DEFAULT nextval('public.concept_index_ths_id_seq'::regclass);


--
-- Name: concept_snapshots id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.concept_snapshots ALTER COLUMN id SET DEFAULT nextval('public.concept_snapshots_id_seq'::regclass);


--
-- Name: concepts id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.concepts ALTER COLUMN id SET DEFAULT nextval('public.concepts_id_seq'::regclass);


--
-- Name: fin_daily_basics id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_daily_basics ALTER COLUMN id SET DEFAULT nextval('public.fin_daily_basics_id_seq'::regclass);


--
-- Name: fin_reports id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_reports ALTER COLUMN id SET DEFAULT nextval('public.fin_reports_id_seq'::regclass);


--
-- Name: fin_top10_floatholders id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_top10_floatholders ALTER COLUMN id SET DEFAULT nextval('public.fin_top10_floatholders_id_seq'::regclass);


--
-- Name: fin_top10_holders id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_top10_holders ALTER COLUMN id SET DEFAULT nextval('public.fin_top10_holders_id_seq'::regclass);


--
-- Name: mkt_calendars id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_calendars ALTER COLUMN id SET DEFAULT nextval('public.mkt_calendars_id_seq'::regclass);


--
-- Name: mkt_index_members id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_index_members ALTER COLUMN id SET DEFAULT nextval('public.mkt_index_members_id_seq'::regclass);


--
-- Name: mkt_market_dailys id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_market_dailys ALTER COLUMN id SET DEFAULT nextval('public.mkt_market_dailys_id_seq'::regclass);


--
-- Name: mkt_sector_dailys id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_sector_dailys ALTER COLUMN id SET DEFAULT nextval('public.mkt_sector_dailys_id_seq'::regclass);


--
-- Name: pool_operations id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.pool_operations ALTER COLUMN id SET DEFAULT nextval('public.pool_operations_id_seq'::regclass);


--
-- Name: stock_infos id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.stock_infos ALTER COLUMN id SET DEFAULT nextval('public.stock_infos_id_seq'::regclass);


--
-- Name: stock_pools id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.stock_pools ALTER COLUMN id SET DEFAULT nextval('public.stock_pools_id_seq'::regclass);


--
-- Name: sys_collect_task_details id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_collect_task_details ALTER COLUMN id SET DEFAULT nextval('public.sys_collect_task_details_id_seq'::regclass);


--
-- Name: sys_collect_tasks id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_collect_tasks ALTER COLUMN id SET DEFAULT nextval('public.sys_collect_tasks_id_seq'::regclass);


--
-- Name: sys_permissions id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_permissions ALTER COLUMN id SET DEFAULT nextval('public.sys_permissions_id_seq'::regclass);


--
-- Name: sys_role_permissions id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_role_permissions ALTER COLUMN id SET DEFAULT nextval('public.sys_role_permissions_id_seq'::regclass);


--
-- Name: sys_roles id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_roles ALTER COLUMN id SET DEFAULT nextval('public.sys_roles_id_seq'::regclass);


--
-- Name: sys_user_roles id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_user_roles ALTER COLUMN id SET DEFAULT nextval('public.sys_user_roles_id_seq'::regclass);


--
-- Name: sys_users id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_users ALTER COLUMN id SET DEFAULT nextval('public.sys_users_id_seq'::regclass);


--
-- Name: tech_kline_dailys id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_kline_dailys ALTER COLUMN id SET DEFAULT nextval('public.daily_klines_id_seq'::regclass);


--
-- Name: base_adj_factors base_adj_factors_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_adj_factors
    ADD CONSTRAINT base_adj_factors_pkey PRIMARY KEY (id);


--
-- Name: base_dividends base_dividends_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_dividends
    ADD CONSTRAINT base_dividends_pkey PRIMARY KEY (id);


--
-- Name: base_name_changes base_name_changes_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_name_changes
    ADD CONSTRAINT base_name_changes_pkey PRIMARY KEY (id);


--
-- Name: base_suspends base_suspends_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_suspends
    ADD CONSTRAINT base_suspends_pkey PRIMARY KEY (id);


--
-- Name: cap_block_trades cap_block_trades_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_block_trades
    ADD CONSTRAINT cap_block_trades_pkey PRIMARY KEY (id);


--
-- Name: cap_holder_nums cap_holder_nums_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_holder_nums
    ADD CONSTRAINT cap_holder_nums_pkey PRIMARY KEY (id);


--
-- Name: cap_margin_details cap_margin_details_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_margin_details
    ADD CONSTRAINT cap_margin_details_pkey PRIMARY KEY (id);


--
-- Name: cap_margins cap_margins_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_margins
    ADD CONSTRAINT cap_margins_pkey PRIMARY KEY (id);


--
-- Name: cap_moneyflows cap_moneyflows_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_moneyflows
    ADD CONSTRAINT cap_moneyflows_pkey PRIMARY KEY (id);


--
-- Name: cap_top_insts cap_top_insts_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_top_insts
    ADD CONSTRAINT cap_top_insts_pkey PRIMARY KEY (id);


--
-- Name: cap_top_lists cap_top_lists_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_top_lists
    ADD CONSTRAINT cap_top_lists_pkey PRIMARY KEY (id);


--
-- Name: collect_fetchers collect_fetchers_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_fetchers
    ADD CONSTRAINT collect_fetchers_pkey PRIMARY KEY (task_type);


--
-- Name: collect_groups collect_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_groups
    ADD CONSTRAINT collect_groups_pkey PRIMARY KEY (id);


--
-- Name: collect_plan_items collect_plan_items_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_plan_items
    ADD CONSTRAINT collect_plan_items_pkey PRIMARY KEY (id);


--
-- Name: collect_plans collect_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_plans
    ADD CONSTRAINT collect_plans_pkey PRIMARY KEY (id);


--
-- Name: concept_index_ths concept_index_ths_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.concept_index_ths
    ADD CONSTRAINT concept_index_ths_pkey PRIMARY KEY (id);


--
-- Name: concept_snapshots concept_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.concept_snapshots
    ADD CONSTRAINT concept_snapshots_pkey PRIMARY KEY (id);


--
-- Name: concepts concepts_index_code_key; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.concepts
    ADD CONSTRAINT concepts_index_code_key UNIQUE (index_code);


--
-- Name: concepts concepts_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.concepts
    ADD CONSTRAINT concepts_pkey PRIMARY KEY (id);


--
-- Name: tech_kline_dailys daily_klines_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_kline_dailys
    ADD CONSTRAINT daily_klines_pkey PRIMARY KEY (id);


--
-- Name: fin_daily_basics fin_daily_basics_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_daily_basics
    ADD CONSTRAINT fin_daily_basics_pkey PRIMARY KEY (id);


--
-- Name: fin_reports fin_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_reports
    ADD CONSTRAINT fin_reports_pkey PRIMARY KEY (id);


--
-- Name: fin_top10_floatholders fin_top10_floatholders_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_top10_floatholders
    ADD CONSTRAINT fin_top10_floatholders_pkey PRIMARY KEY (id);


--
-- Name: fin_top10_holders fin_top10_holders_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_top10_holders
    ADD CONSTRAINT fin_top10_holders_pkey PRIMARY KEY (id);


--
-- Name: mkt_calendars mkt_calendars_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_calendars
    ADD CONSTRAINT mkt_calendars_pkey PRIMARY KEY (id);


--
-- Name: mkt_index_members mkt_index_members_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_index_members
    ADD CONSTRAINT mkt_index_members_pkey PRIMARY KEY (id);


--
-- Name: mkt_market_dailys mkt_market_dailys_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_market_dailys
    ADD CONSTRAINT mkt_market_dailys_pkey PRIMARY KEY (id);


--
-- Name: mkt_sector_dailys mkt_sector_dailys_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_sector_dailys
    ADD CONSTRAINT mkt_sector_dailys_pkey PRIMARY KEY (id);


--
-- Name: pool_operations pool_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.pool_operations
    ADD CONSTRAINT pool_operations_pkey PRIMARY KEY (id);


--
-- Name: stock_concept_members stock_concept_members_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.stock_concept_members
    ADD CONSTRAINT stock_concept_members_pkey PRIMARY KEY (symbol, concept_id);


--
-- Name: stock_infos stock_infos_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.stock_infos
    ADD CONSTRAINT stock_infos_pkey PRIMARY KEY (id);


--
-- Name: stock_pool_members stock_pool_members_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.stock_pool_members
    ADD CONSTRAINT stock_pool_members_pkey PRIMARY KEY (pool_id, symbol);


--
-- Name: stock_pools stock_pools_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.stock_pools
    ADD CONSTRAINT stock_pools_pkey PRIMARY KEY (id);


--
-- Name: sys_collect_task_details sys_collect_task_details_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_collect_task_details
    ADD CONSTRAINT sys_collect_task_details_pkey PRIMARY KEY (id);


--
-- Name: sys_collect_tasks sys_collect_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_collect_tasks
    ADD CONSTRAINT sys_collect_tasks_pkey PRIMARY KEY (id);


--
-- Name: sys_permissions sys_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_permissions
    ADD CONSTRAINT sys_permissions_pkey PRIMARY KEY (id);


--
-- Name: sys_role_permissions sys_role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_role_permissions
    ADD CONSTRAINT sys_role_permissions_pkey PRIMARY KEY (id);


--
-- Name: sys_roles sys_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_roles
    ADD CONSTRAINT sys_roles_pkey PRIMARY KEY (id);


--
-- Name: sys_user_roles sys_user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_user_roles
    ADD CONSTRAINT sys_user_roles_pkey PRIMARY KEY (id);


--
-- Name: sys_users sys_users_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_users
    ADD CONSTRAINT sys_users_pkey PRIMARY KEY (id);


--
-- Name: base_adj_factors uq_base_adj_factors_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_adj_factors
    ADD CONSTRAINT uq_base_adj_factors_uk UNIQUE (symbol, trade_date);


--
-- Name: base_dividends uq_base_dividends_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_dividends
    ADD CONSTRAINT uq_base_dividends_uk UNIQUE (symbol, end_date, div_proc);


--
-- Name: base_name_changes uq_base_name_change_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.base_name_changes
    ADD CONSTRAINT uq_base_name_change_uk UNIQUE (symbol, start_date);


--
-- Name: cap_holder_nums uq_cap_holder_nums_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_holder_nums
    ADD CONSTRAINT uq_cap_holder_nums_uk UNIQUE (symbol, end_date);


--
-- Name: cap_margin_details uq_cap_margin_details_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_margin_details
    ADD CONSTRAINT uq_cap_margin_details_uk UNIQUE (symbol, trade_date);


--
-- Name: cap_margins uq_cap_margins_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_margins
    ADD CONSTRAINT uq_cap_margins_uk UNIQUE (exchange_id, trade_date);


--
-- Name: cap_moneyflows uq_cap_moneyflow_symbol_date; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_moneyflows
    ADD CONSTRAINT uq_cap_moneyflow_symbol_date UNIQUE (symbol, trade_date);


--
-- Name: cap_top_lists uq_cap_top_lists_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.cap_top_lists
    ADD CONSTRAINT uq_cap_top_lists_uk UNIQUE (trade_date, symbol, reason);


--
-- Name: concept_index_ths uq_concept_index_th_code_date; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.concept_index_ths
    ADD CONSTRAINT uq_concept_index_th_code_date UNIQUE (index_code, trade_date);


--
-- Name: fin_daily_basics uq_fin_daily_basics_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_daily_basics
    ADD CONSTRAINT uq_fin_daily_basics_uk UNIQUE (symbol, trade_date);


--
-- Name: fin_reports uq_fin_reports_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_reports
    ADD CONSTRAINT uq_fin_reports_uk UNIQUE (symbol, end_date, report_type);


--
-- Name: fin_top10_floatholders uq_fin_top10_floatholders_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_top10_floatholders
    ADD CONSTRAINT uq_fin_top10_floatholders_uk UNIQUE (symbol, end_date, ann_date, holder_name);


--
-- Name: fin_top10_holders uq_fin_top10_holders_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.fin_top10_holders
    ADD CONSTRAINT uq_fin_top10_holders_uk UNIQUE (symbol, end_date, ann_date, holder_name);


--
-- Name: mkt_calendars uq_mkt_calendars_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_calendars
    ADD CONSTRAINT uq_mkt_calendars_uk UNIQUE (cal_date, exchange);


--
-- Name: mkt_index_members uq_mkt_index_members_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_index_members
    ADD CONSTRAINT uq_mkt_index_members_uk UNIQUE (sector_type, sector_code, symbol, effective_date);


--
-- Name: mkt_market_dailys uq_mkt_market_dailys_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_market_dailys
    ADD CONSTRAINT uq_mkt_market_dailys_uk UNIQUE (market, trade_date);


--
-- Name: mkt_sector_dailys uq_mkt_sector_dailys_uk; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.mkt_sector_dailys
    ADD CONSTRAINT uq_mkt_sector_dailys_uk UNIQUE (sector_type, sector_code, trade_date);


--
-- Name: collect_plan_items uq_plan_task_type; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_plan_items
    ADD CONSTRAINT uq_plan_task_type UNIQUE (plan_id, task_type);


--
-- Name: tech_kline_dailys uq_tech_kline_symbol_date; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.tech_kline_dailys
    ADD CONSTRAINT uq_tech_kline_symbol_date UNIQUE (symbol, date);


--
-- Name: ix_base_adj_factors_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_adj_factors_date ON public.base_adj_factors USING btree (trade_date);


--
-- Name: ix_base_adj_factors_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_adj_factors_symbol ON public.base_adj_factors USING btree (symbol);


--
-- Name: ix_base_adj_factors_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_adj_factors_symbol_date ON public.base_adj_factors USING btree (symbol, trade_date);


--
-- Name: ix_base_dividends_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_dividends_date ON public.base_dividends USING btree (end_date);


--
-- Name: ix_base_dividends_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_dividends_symbol ON public.base_dividends USING btree (symbol);


--
-- Name: ix_base_name_changes_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_name_changes_symbol ON public.base_name_changes USING btree (symbol);


--
-- Name: ix_base_suspends_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_suspends_date ON public.base_suspends USING btree (trade_date);


--
-- Name: ix_base_suspends_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_suspends_symbol ON public.base_suspends USING btree (symbol);


--
-- Name: ix_base_suspends_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_base_suspends_symbol_date ON public.base_suspends USING btree (symbol, trade_date);


--
-- Name: ix_cap_block_trades_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_block_trades_date ON public.cap_block_trades USING btree (trade_date);


--
-- Name: ix_cap_block_trades_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_block_trades_symbol ON public.cap_block_trades USING btree (symbol);


--
-- Name: ix_cap_block_trades_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_block_trades_symbol_date ON public.cap_block_trades USING btree (symbol, trade_date);


--
-- Name: ix_cap_holder_nums_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_holder_nums_date ON public.cap_holder_nums USING btree (end_date);


--
-- Name: ix_cap_holder_nums_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_holder_nums_symbol ON public.cap_holder_nums USING btree (symbol);


--
-- Name: ix_cap_margin_details_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_margin_details_date ON public.cap_margin_details USING btree (trade_date);


--
-- Name: ix_cap_margin_details_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_margin_details_symbol ON public.cap_margin_details USING btree (symbol);


--
-- Name: ix_cap_margin_details_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_margin_details_symbol_date ON public.cap_margin_details USING btree (symbol, trade_date);


--
-- Name: ix_cap_margins_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_margins_date ON public.cap_margins USING btree (trade_date);


--
-- Name: ix_cap_moneyflow_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_moneyflow_date ON public.cap_moneyflows USING btree (trade_date);


--
-- Name: ix_cap_moneyflow_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_moneyflow_symbol ON public.cap_moneyflows USING btree (symbol);


--
-- Name: ix_cap_moneyflow_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_moneyflow_symbol_date ON public.cap_moneyflows USING btree (symbol, trade_date);


--
-- Name: ix_cap_moneyflows_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_moneyflows_symbol ON public.cap_moneyflows USING btree (symbol);


--
-- Name: ix_cap_top_insts_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_top_insts_date ON public.cap_top_insts USING btree (trade_date);


--
-- Name: ix_cap_top_insts_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_top_insts_symbol ON public.cap_top_insts USING btree (symbol);


--
-- Name: ix_cap_top_insts_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_top_insts_symbol_date ON public.cap_top_insts USING btree (symbol, trade_date);


--
-- Name: ix_cap_top_lists_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_top_lists_date ON public.cap_top_lists USING btree (trade_date);


--
-- Name: ix_cap_top_lists_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_top_lists_symbol ON public.cap_top_lists USING btree (symbol);


--
-- Name: ix_cap_top_lists_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_cap_top_lists_symbol_date ON public.cap_top_lists USING btree (symbol, trade_date);


--
-- Name: ix_collect_plan_items_plan_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_plan_items_plan_id ON public.collect_plan_items USING btree (plan_id);


--
-- Name: ix_concept_index_th_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_concept_index_th_date ON public.concept_index_ths USING btree (trade_date);


--
-- Name: ix_concept_index_th_name; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_concept_index_th_name ON public.concept_index_ths USING btree (concept_name);


--
-- Name: ix_concept_member_concept; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_concept_member_concept ON public.stock_concept_members USING btree (concept_id);


--
-- Name: ix_concept_member_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_concept_member_symbol ON public.stock_concept_members USING btree (symbol);


--
-- Name: ix_concept_snapshots_code_captured; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_concept_snapshots_code_captured ON public.concept_snapshots USING btree (index_code, captured_at);


--
-- Name: ix_concept_snapshots_name_captured; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_concept_snapshots_name_captured ON public.concept_snapshots USING btree (concept_name, captured_at);


--
-- Name: ix_concepts_active; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_concepts_active ON public.concepts USING btree (is_active) WHERE (is_active = true);


--
-- Name: ix_concepts_name; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_concepts_name ON public.concepts USING btree (name);


--
-- Name: ix_daily_klines_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_daily_klines_symbol ON public.tech_kline_dailys USING btree (symbol);


--
-- Name: ix_fin_daily_basics_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_daily_basics_date ON public.fin_daily_basics USING btree (trade_date);


--
-- Name: ix_fin_daily_basics_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_daily_basics_symbol ON public.fin_daily_basics USING btree (symbol);


--
-- Name: ix_fin_daily_basics_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_daily_basics_symbol_date ON public.fin_daily_basics USING btree (symbol, trade_date);


--
-- Name: ix_fin_reports_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_reports_symbol ON public.fin_reports USING btree (symbol);


--
-- Name: ix_fin_reports_symbol_end; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_reports_symbol_end ON public.fin_reports USING btree (symbol, end_date);


--
-- Name: ix_fin_top10_floatholders_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_top10_floatholders_date ON public.fin_top10_floatholders USING btree (end_date);


--
-- Name: ix_fin_top10_floatholders_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_top10_floatholders_symbol ON public.fin_top10_floatholders USING btree (symbol);


--
-- Name: ix_fin_top10_holders_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_top10_holders_date ON public.fin_top10_holders USING btree (end_date);


--
-- Name: ix_fin_top10_holders_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_fin_top10_holders_symbol ON public.fin_top10_holders USING btree (symbol);


--
-- Name: ix_mkt_calendars_exchange; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_mkt_calendars_exchange ON public.mkt_calendars USING btree (exchange);


--
-- Name: ix_mkt_calendars_exchange_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_mkt_calendars_exchange_date ON public.mkt_calendars USING btree (exchange, cal_date);


--
-- Name: ix_mkt_index_members_sector; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_mkt_index_members_sector ON public.mkt_index_members USING btree (sector_type, sector_code);


--
-- Name: ix_mkt_index_members_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_mkt_index_members_symbol ON public.mkt_index_members USING btree (symbol);


--
-- Name: ix_mkt_market_dailys_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_mkt_market_dailys_date ON public.mkt_market_dailys USING btree (trade_date);


--
-- Name: ix_mkt_market_dailys_market_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_mkt_market_dailys_market_date ON public.mkt_market_dailys USING btree (market, trade_date);


--
-- Name: ix_mkt_sector_dailys_code; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_mkt_sector_dailys_code ON public.mkt_sector_dailys USING btree (sector_code);


--
-- Name: ix_mkt_sector_dailys_type_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_mkt_sector_dailys_type_date ON public.mkt_sector_dailys USING btree (sector_type, trade_date);


--
-- Name: ix_pool_operations_created_at; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_pool_operations_created_at ON public.pool_operations USING btree (created_at);


--
-- Name: ix_pool_operations_pool_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_pool_operations_pool_id ON public.pool_operations USING btree (pool_id);


--
-- Name: ix_pool_operations_pool_time; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_pool_operations_pool_time ON public.pool_operations USING btree (pool_id, created_at);


--
-- Name: ix_pool_operations_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_pool_operations_status ON public.pool_operations USING btree (status);


--
-- Name: ix_pool_operations_type_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_pool_operations_type_status ON public.pool_operations USING btree (operation_type, status);


--
-- Name: ix_stock_infos_area; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_infos_area ON public.stock_infos USING btree (area);


--
-- Name: ix_stock_infos_exchange; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_infos_exchange ON public.stock_infos USING btree (exchange);


--
-- Name: ix_stock_infos_list_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_infos_list_status ON public.stock_infos USING btree (list_status);


--
-- Name: ix_stock_infos_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE UNIQUE INDEX ix_stock_infos_symbol ON public.stock_infos USING btree (symbol);


--
-- Name: ix_stock_infos_ts_code; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_infos_ts_code ON public.stock_infos USING btree (ts_code);


--
-- Name: ix_stock_pool_members_pool_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_pool_members_pool_id ON public.stock_pool_members USING btree (pool_id);


--
-- Name: ix_stock_pool_members_symbol; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_pool_members_symbol ON public.stock_pool_members USING btree (symbol);


--
-- Name: ix_stock_pools_is_default; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_pools_is_default ON public.stock_pools USING btree (is_default);


--
-- Name: ix_stock_pools_name; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_pools_name ON public.stock_pools USING btree (name);


--
-- Name: ix_stock_pools_owner_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_pools_owner_id ON public.stock_pools USING btree (owner_id);


--
-- Name: ix_stock_pools_pool_type; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_pools_pool_type ON public.stock_pools USING btree (pool_type);


--
-- Name: ix_stock_pools_updated_at; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_stock_pools_updated_at ON public.stock_pools USING btree (updated_at);


--
-- Name: ix_sys_collect_task_details_task_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_collect_task_details_task_id ON public.sys_collect_task_details USING btree (task_id);


--
-- Name: ix_sys_collect_tasks_group_run_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_collect_tasks_group_run_id ON public.sys_collect_tasks USING btree (group_run_id);


--
-- Name: ix_sys_collect_tasks_plan_run_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_collect_tasks_plan_run_id ON public.sys_collect_tasks USING btree (plan_run_id);


--
-- Name: ix_sys_collect_tasks_type_time; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_collect_tasks_type_time ON public.sys_collect_tasks USING btree (task_type, started_at);


--
-- Name: ix_sys_permissions_code; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE UNIQUE INDEX ix_sys_permissions_code ON public.sys_permissions USING btree (code);


--
-- Name: ix_sys_permissions_resource; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_permissions_resource ON public.sys_permissions USING btree (resource);


--
-- Name: ix_sys_role_permissions_permission_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_role_permissions_permission_id ON public.sys_role_permissions USING btree (permission_id);


--
-- Name: ix_sys_role_permissions_role_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_role_permissions_role_id ON public.sys_role_permissions USING btree (role_id);


--
-- Name: ix_sys_roles_code; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE UNIQUE INDEX ix_sys_roles_code ON public.sys_roles USING btree (code);


--
-- Name: ix_sys_user_roles_role_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_user_roles_role_id ON public.sys_user_roles USING btree (role_id);


--
-- Name: ix_sys_user_roles_user_id; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_user_roles_user_id ON public.sys_user_roles USING btree (user_id);


--
-- Name: ix_sys_users_email; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE UNIQUE INDEX ix_sys_users_email ON public.sys_users USING btree (email);


--
-- Name: ix_sys_users_is_active; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_sys_users_is_active ON public.sys_users USING btree (is_active);


--
-- Name: ix_tech_kline_symbol_date; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_tech_kline_symbol_date ON public.tech_kline_dailys USING btree (symbol, date);


--
-- Name: uq_sys_role_permissions_role_perm; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE UNIQUE INDEX uq_sys_role_permissions_role_perm ON public.sys_role_permissions USING btree (role_id, permission_id);


--
-- Name: uq_sys_user_roles_user_role; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE UNIQUE INDEX uq_sys_user_roles_user_role ON public.sys_user_roles USING btree (user_id, role_id);


--
-- Name: collect_plan_items collect_plan_items_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_plan_items
    ADD CONSTRAINT collect_plan_items_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.collect_plans(id) ON DELETE CASCADE;


--
-- Name: collect_plan_items collect_plan_items_task_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_plan_items
    ADD CONSTRAINT collect_plan_items_task_type_fkey FOREIGN KEY (task_type) REFERENCES public.collect_fetchers(task_type);


--
-- Name: pool_operations pool_operations_pool_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.pool_operations
    ADD CONSTRAINT pool_operations_pool_id_fkey FOREIGN KEY (pool_id) REFERENCES public.stock_pools(id) ON DELETE SET NULL;


--
-- Name: stock_pool_members stock_pool_members_pool_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.stock_pool_members
    ADD CONSTRAINT stock_pool_members_pool_id_fkey FOREIGN KEY (pool_id) REFERENCES public.stock_pools(id) ON DELETE CASCADE;


--
-- Name: sys_role_permissions sys_role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_role_permissions
    ADD CONSTRAINT sys_role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.sys_permissions(id) ON DELETE CASCADE;


--
-- Name: sys_role_permissions sys_role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_role_permissions
    ADD CONSTRAINT sys_role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.sys_roles(id) ON DELETE CASCADE;


--
-- Name: sys_user_roles sys_user_roles_granted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_user_roles
    ADD CONSTRAINT sys_user_roles_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES public.sys_users(id) ON DELETE SET NULL;


--
-- Name: sys_user_roles sys_user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_user_roles
    ADD CONSTRAINT sys_user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.sys_roles(id) ON DELETE CASCADE;


--
-- Name: sys_user_roles sys_user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.sys_user_roles
    ADD CONSTRAINT sys_user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.sys_users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 61FCHjRpDjbQXb6PfLvxFeTIsB4VHnRsKXiOfe154pUAgPKcaUyUeznVJGWWkon

