--
-- PostgreSQL database dump
--

\restrict dqhC1KS3VRePOtUN1kvM2dLGP9Hn9fYZhyZDmRYFFv0hYCSkYIYbmJO0E42G9k8

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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: collect_logs; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_logs (
    task_id character varying(64) NOT NULL,
    facet character varying(32) DEFAULT ''::character varying NOT NULL,
    name character varying(64) DEFAULT ''::character varying NOT NULL,
    kind character varying(32) DEFAULT ''::character varying NOT NULL,
    mode character varying(16) DEFAULT 'manual'::character varying NOT NULL,
    trigger_source character varying(16) DEFAULT 'manual'::character varying NOT NULL,
    trigger_user character varying(64),
    params_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    range_start date,
    range_end date,
    status character varying(16) DEFAULT 'queued'::character varying NOT NULL,
    progress smallint DEFAULT 0 NOT NULL,
    total integer DEFAULT 0 NOT NULL,
    done integer DEFAULT 0 NOT NULL,
    success integer DEFAULT 0 NOT NULL,
    fail integer DEFAULT 0 NOT NULL,
    skip integer DEFAULT 0 NOT NULL,
    saved_total bigint DEFAULT 0 NOT NULL,
    message text,
    error text,
    detail jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    duration_ms integer,
    cancel_requested boolean DEFAULT false NOT NULL,
    cancelled_at timestamp with time zone,
    parent_task_id character varying(64),
    CONSTRAINT ck_collect_logs_counters CHECK (((total >= 0) AND (done >= 0) AND (success >= 0) AND (fail >= 0) AND (skip >= 0) AND (saved_total >= 0))),
    CONSTRAINT ck_collect_logs_done_le_total CHECK (((done <= total) OR (total = 0))),
    CONSTRAINT ck_collect_logs_kind CHECK (((kind)::text = ANY ((ARRAY[''::character varying, 'collect'::character varying, 'incremental'::character varying, 'full'::character varying, 'realtime'::character varying, 'both'::character varying])::text[]))),
    CONSTRAINT ck_collect_logs_mode CHECK (((mode)::text = ANY ((ARRAY['condition'::character varying, 'full'::character varying, 'schedule'::character varying, 'manual'::character varying])::text[]))),
    CONSTRAINT ck_collect_logs_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'done'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT ck_collect_logs_trigger_source CHECK (((trigger_source)::text = ANY ((ARRAY['manual'::character varying, 'schedule'::character varying, 'api'::character varying, 'retry'::character varying])::text[])))
);


ALTER TABLE public.collect_logs OWNER TO zhouch;

--
-- Name: TABLE collect_logs; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON TABLE public.collect_logs IS '采集任务日志：一行 = 一次采集任务（Collector 写，Java 只读）';


--
-- Name: COLUMN collect_logs.task_id; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.task_id IS '任务 ID（hex，Collector 生成，两端一致的关联键）';


--
-- Name: COLUMN collect_logs.facet; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.facet IS '五分类数据面：tech/capital/fundamental/news/sentiment';


--
-- Name: COLUMN collect_logs.name; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.name IS 'service 名（= collector 的 name 属性，日志关联键）';


--
-- Name: COLUMN collect_logs.kind; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.kind IS '采集方式（本次执行）：incremental/full';


--
-- Name: COLUMN collect_logs.mode; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.mode IS '编排来源：manual/schedule';


--
-- Name: COLUMN collect_logs.total; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.total IS '计划总步数（步数口径，不是行数）';


--
-- Name: COLUMN collect_logs.saved_total; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.saved_total IS '实际落库行数（行数口径，唯一非步数字段）';


--
-- Name: COLUMN collect_logs.detail; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.detail IS '每步明细 JSONB 数组（排查用）';


--
-- Name: COLUMN collect_logs.parent_task_id; Type: COMMENT; Schema: public; Owner: zhouch
--

COMMENT ON COLUMN public.collect_logs.parent_task_id IS '续跑/重试时指向原任务';


--
-- Name: collect_logs_legacy_20261029; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_logs_legacy_20261029 (
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


ALTER TABLE public.collect_logs_legacy_20261029 OWNER TO zhouch;

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
-- Name: pool_operations id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.pool_operations ALTER COLUMN id SET DEFAULT nextval('public.pool_operations_id_seq'::regclass);


--
-- Name: stock_pools id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.stock_pools ALTER COLUMN id SET DEFAULT nextval('public.stock_pools_id_seq'::regclass);


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
-- Name: collect_logs_legacy_20261029 collect_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_logs_legacy_20261029
    ADD CONSTRAINT collect_logs_pkey PRIMARY KEY (id);


--
-- Name: collect_logs collect_logs_pkey1; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_logs
    ADD CONSTRAINT collect_logs_pkey1 PRIMARY KEY (task_id);


--
-- Name: pool_operations pool_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.pool_operations
    ADD CONSTRAINT pool_operations_pkey PRIMARY KEY (id);


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
-- Name: idx_collect_logs_service_name; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX idx_collect_logs_service_name ON public.collect_logs_legacy_20261029 USING btree (service_name);


--
-- Name: idx_collect_logs_service_time; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX idx_collect_logs_service_time ON public.collect_logs_legacy_20261029 USING btree (service_name, started_at DESC);


--
-- Name: idx_collect_logs_started_at; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX idx_collect_logs_started_at ON public.collect_logs_legacy_20261029 USING btree (started_at DESC);


--
-- Name: idx_collect_logs_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX idx_collect_logs_status ON public.collect_logs_legacy_20261029 USING btree (status);


--
-- Name: ix_collect_logs_created; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_logs_created ON public.collect_logs USING btree (created_at DESC);


--
-- Name: ix_collect_logs_facet; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_logs_facet ON public.collect_logs USING btree (facet);


--
-- Name: ix_collect_logs_name_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_logs_name_status ON public.collect_logs USING btree (name, status);


--
-- Name: ix_collect_logs_status_created; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_logs_status_created ON public.collect_logs USING btree (status, created_at DESC);


--
-- Name: ix_collect_logs_trigger_source; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_logs_trigger_source ON public.collect_logs USING btree (trigger_source, created_at DESC);


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
-- Name: uq_sys_role_permissions_role_perm; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE UNIQUE INDEX uq_sys_role_permissions_role_perm ON public.sys_role_permissions USING btree (role_id, permission_id);


--
-- Name: uq_sys_user_roles_user_role; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE UNIQUE INDEX uq_sys_user_roles_user_role ON public.sys_user_roles USING btree (user_id, role_id);


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

\unrestrict dqhC1KS3VRePOtUN1kvM2dLGP9Hn9fYZhyZDmRYFFv0hYCSkYIYbmJO0E42G9k8

