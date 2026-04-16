<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar';
	import ServerSelector from '$lib/components/mainviews/server/components/serverselection.svelte';
	import SidebarFooter from '$lib/components/mainviews/server/components/sidebarfooter.svelte';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { onMount } from 'svelte';
	import type { Component } from 'svelte';
	import type { IconProps } from '@lucide/svelte';
	import { navigate } from 'svelte5-router';
	import type { ServerSubview } from '$lib/components/mainviews/server/server-subroutes';
	import Gauge from '@lucide/svelte/icons/gauge';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import Users from '@lucide/svelte/icons/users';
	import SquareTerminal from '@lucide/svelte/icons/square-terminal';
	import ScrollText from '@lucide/svelte/icons/scroll-text';
	import Download from '@lucide/svelte/icons/download';
	import Server from '@lucide/svelte/icons/server';
	import Folders from '@lucide/svelte/icons/folders';

	interface SidebarNavItem {
		name: string;
		icon: Component<IconProps>;
		subview: ServerSubview;
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
		{ name: 'Dashboard', icon: Gauge, subview: 'dashboard' },
		{ name: 'Properties', icon: Settings2, subview: 'properties' },
		{ name: 'Mods', icon: Download, subview: 'mods' },
		{ name: 'Console', icon: SquareTerminal, subview: 'console' },
		{ name: 'Server', icon: Server, subview: 'server' },
		{ name: 'Files', icon: Folders, subview: 'files' },
		{ name: 'Logs', icon: ScrollText, subview: 'logs' }
	];

	let {
		newServer = () => {},
		activeSubview = 'dashboard'
	}: {
		newServer?: () => void;
		activeSubview?: ServerSubview;
	} = $props();

	function goToSubview(subview: ServerSubview): void {
		navigate(`/servers/${subview}`);
	}
</script>

<Sidebar.Root collapsible="icon">
	<Sidebar.Header>
		<ServerSelector {newServer} />
	</Sidebar.Header>
	<Separator />
	<Sidebar.Content>
		<Sidebar.Menu class="mt-2">
			{#each serverMenuItems as item (item.name)}
				{@const Icon = item.icon}
				<Sidebar.MenuItem class="md-0.5 mt-0.5 mr-2 ml-2">
					<Sidebar.MenuButton
						isActive={activeSubview === item.subview}
						onclick={() => goToSubview(item.subview)}
					>
						<Icon class="mr-2" />
						{item.name}
					</Sidebar.MenuButton>
				</Sidebar.MenuItem>
			{/each}
		</Sidebar.Menu>
		<div class="mt-auto">
			<Sidebar.Menu>
				{#if isAdminUser}
					<Sidebar.MenuItem class="md-0.5 mt-0.5 mr-2 ml-2">
						<Sidebar.MenuButton
							isActive={activeSubview === 'admin'}
							onclick={() => goToSubview('admin')}
						>
							<Users class="mr-2" />
							Admin
						</Sidebar.MenuButton>
					</Sidebar.MenuItem>
					<Sidebar.MenuItem class="md-0.5 mt-0.5 mr-2 ml-2">
						<Sidebar.MenuButton
							isActive={activeSubview === 'settings'}
							onclick={() => goToSubview('settings')}
						>
							<Settings2 class="mr-2" />
							Settings
						</Sidebar.MenuButton>
					</Sidebar.MenuItem>
				{/if}
			</Sidebar.Menu>
		</div>
	</Sidebar.Content>
	<Sidebar.Footer>
		<SidebarFooter />
	</Sidebar.Footer>
</Sidebar.Root>
