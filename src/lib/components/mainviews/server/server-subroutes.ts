export const SERVER_SUBROUTES = [
	'dashboard',
	'properties',
	'mods',
	'console',
	'server',
	'files',
	'logs',
	'admin',
	'settings'
] as const;

export type ServerSubview = (typeof SERVER_SUBROUTES)[number];

export const SERVER_SUBROUTE_LABELS: Record<ServerSubview, string> = {
	dashboard: 'Dashboard',
	properties: 'Properties',
	mods: 'Mods',
	console: 'Console',
	server: 'Server',
	files: 'Files',
	logs: 'Logs',
	admin: 'Admin',
	settings: 'Settings'
};

export function isServerSubview(value: string): value is ServerSubview {
	return (SERVER_SUBROUTES as readonly string[]).includes(value);
}
