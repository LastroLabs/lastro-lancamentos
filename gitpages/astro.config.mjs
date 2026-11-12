// @ts-check

import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";
import starlightThemeRapidePlugin from "starlight-theme-rapide";

export default defineConfig({
	site: "https://lastrolabs.github.io",
	base: "/lastro-lancamentos/",
	markdown:{
		gfm:true,
	},
	integrations: [
		starlight({
			plugins: [starlightThemeRapidePlugin()],
			title: "Lastro",
			description:
				"Documentação do Lastro: do extrato bancário ao lançamento contábil pronto para importar no Domínio.",
			social: [
				{
					icon: "github",
					label: "GitHub",
					href: "https://github.com/LastroLabs/lastro-lancamentos",
				},
			],
			customCss: ['./src/styles/custom.css'],
			sidebar: [
				{
					label: "Início",
					items: [
						{ label: "O que é o Lastro", slug: "home/sobre" },
					],
				},
				{
					label: "Visão",
					items: [
						{ label: "Cenário e dor", slug: "visao/cenario" },
						{ label: "Solução", slug: "visao/solucao" },
						{ label: "Requisitos v0.2", slug: "visao/requisitos" },
						{ label: "Escopo do MVP", slug: "visao/escopo-mvp" },
						{ label: "Cronograma", slug: "visao/cronograma" },
					],
				},
				{
					label: "Fluxo de desenvolvimento",
					items: [
						{ label: "Por que um harness", slug: "fluxo/visao-geral" },
						{ label: "O ritmo da semana", slug: "fluxo/semana" },
						{ label: "Ciclo de uma feature", slug: "fluxo/ciclo-da-feature" },
						{ label: "Quando algo trava", slug: "fluxo/quando-trava" },
					],
				},
				{
					label: "Decisões",
					items: [
						{ label: "Índice de decisões", slug: "decisoes" },
						{ label: "Arquitetura do sistema", slug: "decisoes/arquitetura" },
						{ label: "Banco de dados", slug: "decisoes/banco-de-dados" },
						{ label: "Avaliação com LLM e modelos", slug: "decisoes/avaliacao-llm" },
						{ label: "UX/UI", slug: "decisoes/ux-ui" },
					],
				},
				{
					label: "Arquitetura",
					items: [
						{ label: "Visão geral", slug: "arquitetura/visao-geral" },
						{ label: "Stack", slug: "arquitetura/stack" },
						{ label: "Dados", slug: "arquitetura/dados" },
						{ label: "IA", slug: "arquitetura/ia" },
						{ label: "Segurança e LGPD", slug: "arquitetura/seguranca" },
					],
				},
				{
					label: "Harness",
					items: [
						{ label: "Documentos e comandos", slug: "harness/documentos-e-comandos" },
						{ label: "Regras e revisão de PR", slug: "harness/regras" },
					],
				},
				{
					label: "Equipe e processo",
					items: [
						{ label: "Equipe", slug: "home/equipe" },
					],
				},
			],
		}),
	],
});
