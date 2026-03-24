<script lang="ts">
	import * as Avatar from "$lib/components/ui/avatar/index.js";
	import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";

	let { username }: { username: string } = $props();

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

<DropdownMenu.Root>
	<DropdownMenu.Trigger>
		<Avatar.Root>
			<Avatar.Fallback>{username.slice(0, 1)}</Avatar.Fallback>
		</Avatar.Root>
	</DropdownMenu.Trigger>
	<DropdownMenu.Content>
		<DropdownMenu.Group>
			<DropdownMenu.Label>Hello, {username}.</DropdownMenu.Label>
			<DropdownMenu.Separator />
			<DropdownMenu.Item>Reset Password</DropdownMenu.Item>
			<DropdownMenu.Item onclick={handleLogout}>Logout</DropdownMenu.Item>
		</DropdownMenu.Group>
	</DropdownMenu.Content>
</DropdownMenu.Root>

