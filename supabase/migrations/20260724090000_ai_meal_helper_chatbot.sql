-- AI meal helper: prompt versioning, safe operational logs, and short-lived chat history.

CREATE TABLE public.prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_name TEXT NOT NULL,
  version INTEGER NOT NULL,
  prompt_content TEXT NOT NULL,
  temperature NUMERIC(3, 2) NOT NULL DEFAULT 0.20 CHECK (temperature >= 0 AND temperature <= 1),
  is_active BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (service_name, version)
);

CREATE UNIQUE INDEX prompt_templates_one_active_idx
  ON public.prompt_templates (service_name) WHERE is_active = true;

CREATE TABLE public.ai_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID NOT NULL,
  user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
  stage TEXT NOT NULL CHECK (stage IN ('validation', 'guardrail', 'main_chat')),
  model TEXT,
  prompt_version INTEGER,
  input_tokens INTEGER,
  output_tokens INTEGER,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  estimated_cost_usd NUMERIC(12, 8),
  status_code INTEGER NOT NULL,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ai_logs_user_stage_created_idx ON public.ai_logs (user_id, stage, created_at DESC);
CREATE INDEX ai_logs_created_idx ON public.ai_logs (created_at DESC);

CREATE TABLE public.chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  conversation_id UUID NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL CHECK (char_length(content) BETWEEN 1 AND 4000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX chat_messages_user_conversation_created_idx
  ON public.chat_messages (user_id, conversation_id, created_at ASC);

CREATE OR REPLACE FUNCTION public.set_prompt_template_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER prompt_templates_set_updated_at
  BEFORE UPDATE ON public.prompt_templates
  FOR EACH ROW EXECUTE FUNCTION public.set_prompt_template_updated_at();

ALTER TABLE public.prompt_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins can manage prompt templates"
  ON public.prompt_templates FOR ALL
  USING (public.is_admin(auth.uid()))
  WITH CHECK (public.is_admin(auth.uid()));

CREATE POLICY "Admins can view AI logs"
  ON public.ai_logs FOR SELECT
  USING (public.is_admin(auth.uid()));

CREATE POLICY "Users can view own chat messages"
  ON public.chat_messages FOR SELECT
  USING (auth.uid() = user_id);

INSERT INTO public.prompt_templates (service_name, version, prompt_content, temperature, is_active)
VALUES (
  'meal_helper_chatbot',
  1,
  'You are Hakchelin, a helpful university meal-service assistant. Answer in the user''s language. Use tools for current menu, the user''s tickets, and points. Do not invent menu data, booking status, prices, policy details, or account information. You can explain how to use the service, but never perform reservations, cancellations, refunds, or point changes. Keep answers concise and friendly.',
  0.20,
  true
)
ON CONFLICT (service_name, version) DO NOTHING;

CREATE OR REPLACE FUNCTION public.purge_expired_chat_messages()
RETURNS INTEGER AS $$
DECLARE v_deleted INTEGER;
BEGIN
  DELETE FROM public.chat_messages
  WHERE created_at < NOW() - INTERVAL '7 days';
  GET DIAGNOSTICS v_deleted = ROW_COUNT;
  RETURN v_deleted;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

REVOKE EXECUTE ON FUNCTION public.purge_expired_chat_messages() FROM anon, authenticated;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
    CREATE EXTENSION IF NOT EXISTS pg_cron;
    PERFORM cron.schedule('hakchelin-purge-chat-messages', '15 3 * * *', 'SELECT public.purge_expired_chat_messages()');
  END IF;
END;
$$;
