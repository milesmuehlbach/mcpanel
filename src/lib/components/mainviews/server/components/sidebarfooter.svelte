<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	// import User from '$lib/components/mainviews/server/components/user.svelte';
	import LogOutIcon from '@lucide/svelte/icons/log-out';

	const sidebar = Sidebar.useSidebar();
	const clamp = (value: number, min = 0, max = 1) => Math.min(Math.max(value, min), max);
	const lerp = (from: number, to: number, progress: number) => from + (to - from) * progress;
	let collapseProgress = $derived(clamp(sidebar.progress));
	let isCollapsed = $derived(collapseProgress > 0.9);
	let logoutButtonStyle = $derived(
		`gap: ${lerp(0.25, 0, collapseProgress).toFixed(4)}rem; padding-inline: ${lerp(0.625, 0.5, collapseProgress).toFixed(4)}rem; will-change: gap, padding;`
	);

	async function handleLogout() {
		sessionStorage.removeItem('token');
		window.location.reload();
	}
</script>

<Button
	variant={collapseProgress > 0.9 ? 'ghost' : 'outline'}
	size="sm"
	class="overflow-hidden"
	style={logoutButtonStyle}
	onclick={handleLogout}
>
	<span data-sidebar="label" class="whitespace-nowrap">Log Out</span>
	<LogOutIcon />
</Button>
<Separator />

<div
	class={`flex w-full ${isCollapsed ? 'flex-col-reverse items-center gap-2' : 'items-center justify-between gap-2'}`}
>
	<Sidebar.Trigger class="size-8 shrink-0 bg-transparent" />
	<!-- <User class="size-8" /> -->
    <!-- disabled on 3/24 because it has severe impacts on sidebar expand/collapse ux -@technodot -->
</div>
