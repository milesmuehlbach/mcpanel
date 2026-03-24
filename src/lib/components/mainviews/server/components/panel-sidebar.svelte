<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar';
	import ServerSelector from '$lib/components/mainviews/server/components/serverselection.svelte';
	import SidebarFooter from '$lib/components/mainviews/server/components/sidebarfooter.svelte';
	import SidebarItem from '$lib/components/mainviews/server/components/sidebaritem.svelte';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { onMount } from 'svelte';
	import type { Component } from 'svelte';
	import type { IconProps } from '@lucide/svelte';
	import Gauge from '@lucide/svelte/icons/gauge';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import ServerCog from '@lucide/svelte/icons/server-cog';
	import Users from '@lucide/svelte/icons/users';
	import SquareTerminal from '@lucide/svelte/icons/square-terminal'
	import ScrollText from '@lucide/svelte/icons/scroll-text';
	import Download from '@lucide/svelte/icons/download';
	import Server from '@lucide/svelte/icons/server';
	import Folders from '@lucide/svelte/icons/folders'

	interface SidebarNavItem {
		name: string;
		icon: Component<IconProps>;
	}

	let isAdminUser = $state(false);

	async function loadPermissions(): Promise<void> {
		const token = sessionStorage.getItem('token');

		if (!token) {
			isAdminUser = false;
			return;
		}

		try {
			const response = await fetch('/api/v1/auth/permissions', {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				isAdminUser = false;
				return;
			}

			const data = (await response.json()) as { permissions?: unknown };
			isAdminUser =
				Array.isArray(data.permissions) &&
				data.permissions.some((permission) => permission === 'admin');
		} catch (error) {
			console.error('Error fetching permissions:', error);
			isAdminUser = false;
		}
	}

	onMount(() => {
		void loadPermissions();
	});

	const serverMenuItems: SidebarNavItem[] = [
		{ name: 'Dashboard', icon: Gauge },
		{ name: 'Properties', icon: Settings2 },
		{ name: 'Mods', icon: Download },
		{ name: 'Console', icon: SquareTerminal },
		{ name: 'Server', icon: Server},
		{ name: 'Files', icon: Folders },
		{ name: 'Logs', icon: ScrollText }
	];

	let { newServer = () => {} }: { newServer?: () => void } = $props();
</script>

<Sidebar.Root collapsible="icon">
	<Sidebar.Header>
		<ServerSelector servertitles={['McPanel Test', 'TechnoDot Server']} iconpath={[]} {newServer} />
	</Sidebar.Header>
	<Sidebar.Content>
		<Sidebar.Group />
		<Sidebar.Menu>
			{#each serverMenuItems as item (item.name)}
				<SidebarItem name={item.name} icon={item.icon} />
			{/each}
		</Sidebar.Menu>
		<Sidebar.Group />
		<Sidebar.Group class="mt-auto align-left">
			<Sidebar.Menu>
				{#if isAdminUser}
					<SidebarItem name="MCPanel Settings" icon={ServerCog} />
					<SidebarItem name="User Management" icon={Users} />
				{/if}
			</Sidebar.Menu>
		</Sidebar.Group>
	</Sidebar.Content>
	<Sidebar.Footer>
		<SidebarFooter />
	</Sidebar.Footer>
</Sidebar.Root>
