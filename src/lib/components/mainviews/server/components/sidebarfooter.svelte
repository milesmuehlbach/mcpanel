<script>
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import LogOutIcon from '@lucide/svelte/icons/log-out';

	const sidebar = Sidebar.useSidebar();
	const clamp = (value, min = 0, max = 1) => Math.min(Math.max(value, min), max);
	const lerp = (from, to, progress) => from + (to - from) * progress;
	let collapseProgress = $derived(clamp(sidebar.progress));
	let logoutButtonStyle = $derived(
		`gap: ${lerp(0.25, 0, collapseProgress).toFixed(4)}rem; padding-inline: ${lerp(0.625, 0.5, collapseProgress).toFixed(4)}rem; will-change: gap, padding;`
	);

	async function handleLogout() {
		const token = sessionStorage.getItem('token');
		if (!token) {
			console.error('No token found, cannot log out.');
			window.location.reload();
			return;
		}
		sessionStorage.removeItem('token');
		window.location.reload();
		return;
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
<Sidebar.Trigger class="size-8 shrink-0 bg-transparent" />
