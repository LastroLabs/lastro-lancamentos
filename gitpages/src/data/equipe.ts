// Equipe do Lastro: papéis e frentes definidos pela líder em 18/11/2026. Os handles não mudam.
// github: usuário do GitHub, sem @. Deixe undefined quando não for informado.

export interface Membro {
	nome: string;
	papel: string;
	frente: string;
	github?: string;
}

export const equipe: Membro[] = [
	{ nome: 'Júlia Santana Campos', papel: 'Líder e Tech Lead', frente: 'Coordenação e curinga', github: 'camposs04' },
	{ nome: 'Caio Nascimento', papel: 'Vice-líder', frente: 'Harness e CI', github: 'caio-nascime' },
	{ nome: 'Arthur Leite', papel: 'Desenvolvedor', frente: 'Segurança', github: 'arthurlleite' },
	{ nome: 'Thomaz Martins', papel: 'Desenvolvedor', frente: 'Documentação', github: 'marrathomaz' },
	{ nome: 'Guilherme Pereira', papel: 'Líder de banco', frente: 'Banco de dados', github: 'guin409' },
	{ nome: 'Raissa Oliveira', papel: 'Desenvolvedora', frente: 'Banco de dados (apoio)', github: 'RaissaOliveira19' },
	{ nome: 'João Sauma', papel: 'Desenvolvedor', frente: 'Front (prototipação das telas)', github: 'jvsauma' },
];

/** Iniciais para o avatar de reserva: primeira letra do primeiro e do último nome. */
export function iniciais(nome: string): string {
	const partes = nome.trim().split(/\s+/);
	return ((partes[0]?.[0] ?? '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
}
