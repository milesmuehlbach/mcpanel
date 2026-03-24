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
		{ name: 'Properties', icon: Settings2 }
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
			{#if isAdminUser}
				<Separator class="m-0.5"/>
				<SidebarItem name="Admin" icon={Settings2} />
			{/if}
		</Sidebar.Menu>
		<Sidebar.Group />
	</Sidebar.Content>
	<Sidebar.Footer>
		<SidebarFooter />
	</Sidebar.Footer>
</Sidebar.Root>
