-- Prompt content is deployment-owned. Browser clients, including administrators,
-- cannot inspect or alter it; the Edge Function reads it with the service role.
DROP POLICY IF EXISTS "Admins can manage prompt templates" ON public.prompt_templates;

REVOKE ALL ON TABLE public.prompt_templates FROM anon, authenticated;
