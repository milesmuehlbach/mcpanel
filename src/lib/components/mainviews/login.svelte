<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import {
		FieldGroup,
		Field,
		FieldLabel,
		FieldDescription,
		FieldError
	} from '$lib/components/ui/field/index.js';

	let { onSuccess = () => {} }: { onSuccess?: () => void } = $props();

	let username = $state('');
	let password = $state('');
	let errordis = $state('');
	const usernameRegex = /^[A-Za-z0-9_-]+$/;
	let isUsernameValid = $derived(username === '' || usernameRegex.test(username));
	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();

		if (!usernameRegex.test(username)) {
			console.error('Invalid username');
			return;
		}

		try {
			const response = await fetch('/api/v1/auth/login', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ username, password })
			});

			if (response.ok) {
				const data = await response.json();
				console.log('Login successful:', data);
				errordis = 'Login Successful : ' + data.message;
				sessionStorage.setItem('token', data.token);
				onSuccess();
			} else {
				const error = await response.json();
				console.error('Login failed:', error);
				errordis = 'Login failed: ' + error.message;
			}
		} catch (err) {
			console.error('An error occurred during login: ', err);
		}
	}
</script>

<Card.Root class="mx-auto w-full max-w-sm">
	<Card.Header>
		<Card.Title class="text-2xl">Login to MCPanel</Card.Title>
	</Card.Header>
	<Card.Content>
		<form onsubmit={handleSubmit}>
			<FieldGroup>
				<Field>
					<FieldLabel for="username">Username</FieldLabel>
					<Input
						id="username"
						name="username"
						type="text"
						placeholder="Username"
						required
						bind:value={username}
						pattern="[-A-Za-z0-9_]+"
					/>
					{#if !isUsernameValid}
						<FieldDescription class="text-destructive">
							Username must only contain a-z, A-Z, 0-9, _ and -
						</FieldDescription>
					{/if}
				</Field>
				<Field>
					<div class="flex items-center">
						<FieldLabel for="password">Password</FieldLabel>
					</div>
					<Input
						id="password"
						name="password"
						type="password"
						required
						placeholder="Password"
						bind:value={password}
					/>
				</Field>
				<Field>
					<Button
						type="submit"
						class="w-full"
						disabled={!isUsernameValid || username === '' || password === ''}
					>
						Login
					</Button>
				</Field>
				<FieldError>{errordis}</FieldError>
			</FieldGroup>
		</form>
	</Card.Content>
</Card.Root>
