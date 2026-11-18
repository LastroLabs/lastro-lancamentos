// Equipe do Lastro, a partir de src/content/docs/home/equipe.mdx (proposta a confirmar no planejamento).
// github: usuário do GitHub, sem @. Deixe undefined quando não for informado.

export interface Membro {
	nome: string;
	papel: string;
	frente: string;
	github?: string;
}

export const equipe: Membro[] = [
	{ nome: 'Júlia Santana Campos', papel: 'Líder e Tech Lead', frente: 'Coordenação técnica', github: 'camposs04' },
	{ nome: 'Caio Nascimento', papel: 'Vice-líder', frente: 'Classificação/IA', github: 'caio-nascime' },
	{ nome: 'Arthur Leite', papel: 'Desenvolvedor', frente: 'Plataforma', github: 'arthurlleite' },
	{ nome: 'Thomaz Martins', papel: 'Desenvolvedor', frente: 'Plataforma', github: 'marrathomaz' },
	{ nome: 'Guilherme Pereira', papel: 'Desenvolvedor', frente: 'Frontend', github: 'guin409' },
	{ nome: 'Raissa Oliveira', papel: 'Desenvolvedora', frente: 'Frontend', github: 'RaissaOliveira19' },
	{ nome: 'João Sauma', papel: 'Desenvolvedor', frente: 'Leitura de bancos', github: 'jvsauma' },
];

/** Iniciais para o avatar de reserva: primeira letra do primeiro e do último nome. */
export function iniciais(nome: string): string {
	const partes = nome.trim().split(/\s+/);
	return ((partes[0]?.[0] ?? '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
}
