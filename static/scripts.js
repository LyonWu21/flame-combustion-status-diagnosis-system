document.addEventListener('DOMContentLoaded', function() {
    // 密码强度检测
    const passwordInput = document.getElementById('password');
    const passwordStrength = document.getElementById('password-strength');

    if (passwordInput && passwordStrength) {
        passwordInput.addEventListener('input', function() {
            const strength = checkPasswordStrength(passwordInput.value);
            passwordStrength.textContent = `Password strength: ${strength}`;
            passwordStrength.style.color = getColorForStrength(strength);
        });
    }

    // 密码匹配验证
    const confirmPasswordInput = document.getElementById('confirm_password');
    const passwordMatch = document.getElementById('password-match');

    if (confirmPasswordInput && passwordMatch) {
        confirmPasswordInput.addEventListener('input', function() {
            if (passwordInput.value === confirmPasswordInput.value) {
                passwordMatch.textContent = "Passwords match!";
                passwordMatch.style.color = "green";
            } else {
                passwordMatch.textContent = "Passwords do not match!";
                passwordMatch.style.color = "red";
            }
        });
    }

    // 页面淡入效果
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
        mainContent.style.opacity = 0;
        setTimeout(() => {
            mainContent.style.transition = 'opacity 2s';
            mainContent.style.opacity = 1;
        }, 100);
    }
});

function checkPasswordStrength(password) {
    if (password.length > 8 && /[A-Z]/.test(password) && /\d/.test(password)) {
        return "Strong";
    } else if (password.length >= 6) {
        return "Moderate";
    } else {
        return "Weak";
    }
}

function getColorForStrength(strength) {
    switch (strength) {
        case "Strong":
            return "green";
        case "Moderate":
            return "orange";
        case "Weak":
            return "red";
        default:
            return "black";
    }
}

let recording = false;

function toggleRecording() {
    recording = !recording;
    const recordBtn = document.getElementById('recordBtn');
    recordBtn.innerText = recording ? '停止录制' : '开始录制';

    // 向服务器发送请求开始/停止录制
    fetch(`/toggle_recording`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ recording: recording }),
    }).then(response => response.json())
        .then(data => {
            console.log(data.message);
        });
}

function fetchFlameProperties() {
    fetch('/get_flame_properties')
        .then(response => response.json())
        .then(data => {
            document.getElementById('flame_signal').innerText = data.flame_signal;
            document.getElementById('flame_stability').innerText = data.flame_stability;
            document.getElementById('flame_length').innerText = data.flame_length;
            document.getElementById('flame_width').innerText = data.flame_width;
            document.getElementById('flame_area').innerText = data.flame_area;
            document.getElementById('average_temp').innerText = data.average_temp;

            updateFlameChart(data);
        });
}

const ctx = document.getElementById('flameChart').getContext('2d');
const flameChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['燃烧运行信号', '燃烧稳定性系数', '火焰长度', '火焰宽度', '火焰面积', '火焰平均温度'],
        datasets: [{
            label: '火焰特性',
            data: [0, 0, 0, 0, 0, 0],
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

function updateFlameChart(data) {
    flameChart.data.datasets[0].data = [
        data.flame_signal,
        data.flame_stability,
        data.flame_length,
        data.flame_width,
        data.flame_area,
        data.average_temp
    ];
    flameChart.update();
}

// 定时刷新火焰参数
setInterval(fetchFlameProperties, 1000);

