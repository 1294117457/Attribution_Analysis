--
-- PostgreSQL database dump
--

\restrict EvsUd4r8M8be8yQHy2tmFJyTwS6EmniBwMgtBG4LfK0Q3wL2mLkq0Ax0dAwVhsZ

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
-- Name: collect_run_log; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_run_log (
    id bigint NOT NULL,
    schedule_id integer,
    service_name character varying(64) NOT NULL,
    trigger_type character varying(16) NOT NULL,
    params jsonb DEFAULT '{}'::jsonb NOT NULL,
    started_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    duration_ms integer,
    status character varying(16) DEFAULT 'running'::character varying NOT NULL,
    total_count integer DEFAULT 0 NOT NULL,
    success_count integer DEFAULT 0 NOT NULL,
    fail_count integer DEFAULT 0 NOT NULL,
    skip_count integer DEFAULT 0 NOT NULL,
    saved_count integer DEFAULT 0 NOT NULL,
    message text,
    error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_collect_run_log_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'success'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE public.collect_run_log OWNER TO zhouch;

--
-- Name: collect_run_log_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.collect_run_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.collect_run_log_id_seq OWNER TO zhouch;

--
-- Name: collect_run_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.collect_run_log_id_seq OWNED BY public.collect_run_log.id;


--
-- Name: collect_schedule; Type: TABLE; Schema: public; Owner: zhouch
--

CREATE TABLE public.collect_schedule (
    id integer NOT NULL,
    service_name character varying(64) NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    trigger_type character varying(16) NOT NULL,
    times text[] DEFAULT '{}'::text[] NOT NULL,
    interval_seconds integer,
    params jsonb DEFAULT '{}'::jsonb NOT NULL,
    concurrency integer DEFAULT 5 NOT NULL,
    display_name character varying(128),
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_collect_schedule_trigger CHECK (((((trigger_type)::text = 'time'::text) AND (times <> '{}'::text[]) AND (interval_seconds IS NULL)) OR (((trigger_type)::text = 'interval'::text) AND (interval_seconds IS NOT NULL) AND (interval_seconds >= 30))))
);


ALTER TABLE public.collect_schedule OWNER TO zhouch;

--
-- Name: collect_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: zhouch
--

CREATE SEQUENCE public.collect_schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.collect_schedule_id_seq OWNER TO zhouch;

--
-- Name: collect_schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: zhouch
--

ALTER SEQUENCE public.collect_schedule_id_seq OWNED BY public.collect_schedule.id;


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
-- Name: collect_run_log id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_run_log ALTER COLUMN id SET DEFAULT nextval('public.collect_run_log_id_seq'::regclass);


--
-- Name: collect_schedule id; Type: DEFAULT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_schedule ALTER COLUMN id SET DEFAULT nextval('public.collect_schedule_id_seq'::regclass);


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
-- Name: collect_run_log collect_run_log_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_run_log
    ADD CONSTRAINT collect_run_log_pkey PRIMARY KEY (id);


--
-- Name: collect_schedule collect_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: zhouch
--

ALTER TABLE ONLY public.collect_schedule
    ADD CONSTRAINT collect_schedule_pkey PRIMARY KEY (id);


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
-- Name: ix_collect_run_log_schedule; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_run_log_schedule ON public.collect_run_log USING btree (schedule_id);


--
-- Name: ix_collect_run_log_service_time; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_run_log_service_time ON public.collect_run_log USING btree (service_name, started_at DESC);


--
-- Name: ix_collect_run_log_status; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_run_log_status ON public.collect_run_log USING btree (status);


--
-- Name: ix_collect_schedule_enabled; Type: INDEX; Schema: public; Owner: zhouch
--

CREATE INDEX ix_collect_schedule_enabled ON public.collect_schedule USING btree (enabled) WHERE (enabled = true);


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

\unrestrict EvsUd4r8M8be8yQHy2tmFJyTwS6EmniBwMgtBG4LfK0Q3wL2mLkq0Ax0dAwVhsZ

