-- v0.18 Mercado Libre Colombia OAuth. No secrets are stored in tables or Git.
create table if not exists public.market_connections (
  source text primary key,
  status text not null check(status in ('APP_REQUIRED','AUTHORIZATION_REQUIRED','READY','TOKEN_EXPIRED','ERROR','DISABLED')),
  client_id text,
  redirect_uri text not null,
  user_id bigint,
  scopes text,
  access_expires_at timestamptz,
  last_refresh_at timestamptz,
  last_error text,
  updated_at timestamptz not null default now()
);

create table if not exists public.market_oauth_states (
  state_hash text primary key,
  source text not null references public.market_connections(source) on delete cascade,
  pkce_secret_id uuid not null,
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.market_connections enable row level security;
alter table public.market_oauth_states enable row level security;
revoke all on public.market_connections,public.market_oauth_states from anon,authenticated;
grant select,insert,update,delete on public.market_connections,public.market_oauth_states to service_role;

insert into public.market_connections(source,status,redirect_uri,last_error)
values('MERCADOLIBRE_MCO','APP_REQUIRED','https://bxsfxydhuaqlkfoicbaz.supabase.co/functions/v1/meli-oauth','Create/authorize a Mercado Libre Colombia application before market search can run.')
on conflict(source) do nothing;

create or replace function public.market_secret_get(p_name text)
returns text language sql security definer
set search_path=public,vault,extensions,pg_catalog
as $$
  select decrypted_secret from vault.decrypted_secrets where name=p_name order by updated_at desc limit 1;
$$;

create or replace function public.market_secret_upsert(p_name text,p_value text,p_description text default '')
returns uuid language plpgsql security definer
set search_path=public,vault,extensions,pg_catalog
as $$
declare v_id uuid;
begin
  if p_name is null or p_name='' or p_value is null or p_value='' then raise exception 'Secret name/value required'; end if;
  select id into v_id from vault.decrypted_secrets where name=p_name order by updated_at desc limit 1;
  if v_id is null then v_id:=vault.create_secret(p_value,p_name,coalesce(p_description,''));
  else perform vault.update_secret(v_id,p_value,p_name,coalesce(p_description,'')); end if;
  return v_id;
end
$$;

create or replace function public.meli_set_app_config(p_client_id text,p_client_secret text)
returns jsonb language plpgsql security definer
set search_path=public,vault,extensions,pg_catalog
as $$
begin
  if p_client_id is null or p_client_id='' or p_client_secret is null or p_client_secret='' then raise exception 'client_id and client_secret required'; end if;
  perform public.market_secret_upsert('meli_client_secret',p_client_secret,'Mercado Libre application client secret');
  update public.market_connections set client_id=p_client_id,status='AUTHORIZATION_REQUIRED',last_error=null,updated_at=now() where source='MERCADOLIBRE_MCO';
  return jsonb_build_object('ok',true,'status','AUTHORIZATION_REQUIRED','redirect_uri',(select redirect_uri from public.market_connections where source='MERCADOLIBRE_MCO'));
end
$$;

create or replace function public.meli_prepare_authorization()
returns jsonb language plpgsql security definer
set search_path=public,vault,extensions,pg_catalog
as $$
declare c record; v_state text; v_state_hash text; v_verifier text; v_challenge text; v_sid uuid; v_url text;
begin
  select * into c from public.market_connections where source='MERCADOLIBRE_MCO';
  if c.client_id is null or public.market_secret_get('meli_client_secret') is null then
    return jsonb_build_object('ok',false,'status','APP_REQUIRED','redirect_uri',c.redirect_uri);
  end if;
  v_state:=encode(extensions.gen_random_bytes(32),'hex');
  v_state_hash:=encode(extensions.digest(v_state,'sha256'),'hex');
  v_verifier:=replace(replace(rtrim(encode(extensions.gen_random_bytes(48),'base64'),'='),'+','-'),'/','_');
  v_challenge:=replace(replace(rtrim(encode(extensions.digest(v_verifier,'sha256'),'base64'),'='),'+','-'),'/','_');
  v_sid:=vault.create_secret(v_verifier,'meli_pkce_'||left(v_state_hash,20),'One-time Mercado Libre PKCE verifier');
  insert into public.market_oauth_states(state_hash,source,pkce_secret_id,expires_at)
  values(v_state_hash,'MERCADOLIBRE_MCO',v_sid,clock_timestamp()+interval '10 minutes');
  v_url:='https://auth.mercadolibre.com.co/authorization?response_type=code&client_id='||extensions.urlencode(c.client_id)||
    '&redirect_uri='||extensions.urlencode(c.redirect_uri)||'&state='||extensions.urlencode(v_state)||
    '&code_challenge='||extensions.urlencode(v_challenge)||'&code_challenge_method=S256';
  return jsonb_build_object('ok',true,'status','AUTHORIZATION_REQUIRED','authorization_url',v_url,'expires_at',clock_timestamp()+interval '10 minutes');
end
$$;

create or replace function public.meli_exchange_authorization_code(p_code text,p_state text)
returns jsonb language plpgsql security definer
set search_path=public,vault,extensions,pg_catalog
as $$
declare c record; st record; v_hash text; v_verifier text; v_secret text; v_resp extensions.http_response; v_json jsonb; v_body text;
begin
  if p_code is null or p_code='' or p_state is null or p_state='' then return jsonb_build_object('ok',false,'status','INVALID_CALLBACK'); end if;
  v_hash:=encode(extensions.digest(p_state,'sha256'),'hex');
  select * into st from public.market_oauth_states where state_hash=v_hash and source='MERCADOLIBRE_MCO' for update;
  if not found or st.used_at is not null or st.expires_at<clock_timestamp() then return jsonb_build_object('ok',false,'status','INVALID_OR_EXPIRED_STATE'); end if;
  select * into c from public.market_connections where source='MERCADOLIBRE_MCO';
  select decrypted_secret into v_verifier from vault.decrypted_secrets where id=st.pkce_secret_id;
  v_secret:=public.market_secret_get('meli_client_secret');
  if c.client_id is null or v_secret is null or v_verifier is null then return jsonb_build_object('ok',false,'status','APP_REQUIRED'); end if;
  v_body:='grant_type=authorization_code&client_id='||extensions.urlencode(c.client_id)||'&client_secret='||extensions.urlencode(v_secret)||
    '&code='||extensions.urlencode(p_code)||'&redirect_uri='||extensions.urlencode(c.redirect_uri)||'&code_verifier='||extensions.urlencode(v_verifier);
  select * into v_resp from extensions.http(row('POST'::extensions.http_method,'https://api.mercadolibre.com/oauth/token'::varchar,
    array[extensions.http_header('accept','application/json')],'application/x-www-form-urlencoded'::varchar,v_body::varchar)::extensions.http_request);
  update public.market_oauth_states set used_at=clock_timestamp() where state_hash=v_hash;
  delete from vault.secrets where id=st.pkce_secret_id;
  if v_resp.status<>200 then
    update public.market_connections set status='ERROR',last_error='OAuth token exchange HTTP '||v_resp.status,updated_at=now() where source='MERCADOLIBRE_MCO';
    return jsonb_build_object('ok',false,'status','TOKEN_EXCHANGE_FAILED','http_status',v_resp.status);
  end if;
  v_json:=v_resp.content::jsonb;
  if nullif(v_json->>'access_token','') is null or nullif(v_json->>'refresh_token','') is null then
    update public.market_connections set status='ERROR',last_error='OAuth response missing token fields',updated_at=now() where source='MERCADOLIBRE_MCO';
    return jsonb_build_object('ok',false,'status','TOKEN_RESPONSE_INVALID');
  end if;
  perform public.market_secret_upsert('meli_access_token',v_json->>'access_token','Mercado Libre rotating access token');
  perform public.market_secret_upsert('meli_refresh_token',v_json->>'refresh_token','Mercado Libre one-use rotating refresh token');
  update public.market_connections set status='READY',user_id=nullif(v_json->>'user_id','')::bigint,scopes=v_json->>'scope',
    access_expires_at=clock_timestamp()+make_interval(secs=>coalesce(nullif(v_json->>'expires_in','')::integer,10800)),last_refresh_at=clock_timestamp(),last_error=null,updated_at=clock_timestamp()
  where source='MERCADOLIBRE_MCO';
  return jsonb_build_object('ok',true,'status','READY','user_id',v_json->>'user_id','expires_in',v_json->>'expires_in');
end
$$;

create or replace function public.meli_refresh_access_token()
returns jsonb language plpgsql security definer
set search_path=public,vault,extensions,pg_catalog
as $$
declare c record; v_secret text; v_refresh text; v_resp extensions.http_response; v_json jsonb; v_body text;
begin
  select * into c from public.market_connections where source='MERCADOLIBRE_MCO' for update;
  if c.client_id is null then return jsonb_build_object('ok',false,'status','APP_REQUIRED'); end if;
  if c.status='READY' and c.access_expires_at>clock_timestamp()+interval '30 minutes' then return jsonb_build_object('ok',true,'status','READY','refreshed',false,'expires_at',c.access_expires_at); end if;
  v_secret:=public.market_secret_get('meli_client_secret'); v_refresh:=public.market_secret_get('meli_refresh_token');
  if v_secret is null or v_refresh is null then
    update public.market_connections set status='AUTHORIZATION_REQUIRED',last_error='Refresh token missing',updated_at=now() where source='MERCADOLIBRE_MCO';
    return jsonb_build_object('ok',false,'status','AUTHORIZATION_REQUIRED');
  end if;
  v_body:='grant_type=refresh_token&client_id='||extensions.urlencode(c.client_id)||'&client_secret='||extensions.urlencode(v_secret)||'&refresh_token='||extensions.urlencode(v_refresh);
  select * into v_resp from extensions.http(row('POST'::extensions.http_method,'https://api.mercadolibre.com/oauth/token'::varchar,
    array[extensions.http_header('accept','application/json')],'application/x-www-form-urlencoded'::varchar,v_body::varchar)::extensions.http_request);
  if v_resp.status<>200 then
    update public.market_connections set status='TOKEN_EXPIRED',last_error='Token refresh HTTP '||v_resp.status,updated_at=now() where source='MERCADOLIBRE_MCO';
    return jsonb_build_object('ok',false,'status','TOKEN_EXPIRED','http_status',v_resp.status);
  end if;
  v_json:=v_resp.content::jsonb;
  perform public.market_secret_upsert('meli_access_token',v_json->>'access_token','Mercado Libre rotating access token');
  perform public.market_secret_upsert('meli_refresh_token',v_json->>'refresh_token','Mercado Libre one-use rotating refresh token');
  update public.market_connections set status='READY',scopes=coalesce(v_json->>'scope',scopes),
    access_expires_at=clock_timestamp()+make_interval(secs=>coalesce(nullif(v_json->>'expires_in','')::integer,10800)),last_refresh_at=clock_timestamp(),last_error=null,updated_at=clock_timestamp()
  where source='MERCADOLIBRE_MCO';
  return jsonb_build_object('ok',true,'status','READY','refreshed',true,'expires_in',v_json->>'expires_in');
end
$$;

revoke all on function public.market_secret_get(text),public.market_secret_upsert(text,text,text),public.meli_set_app_config(text,text),public.meli_prepare_authorization(),public.meli_exchange_authorization_code(text,text),public.meli_refresh_access_token() from public,anon,authenticated;
grant execute on function public.market_secret_get(text),public.market_secret_upsert(text,text,text),public.meli_set_app_config(text,text),public.meli_prepare_authorization(),public.meli_exchange_authorization_code(text,text),public.meli_refresh_access_token() to service_role;
